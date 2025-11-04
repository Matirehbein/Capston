const router = require('express').Router();
const fetch = require('node-fetch'); // <-- ¡NUEVA IMPORTACIÓN!
const cors = require('cors'); // <--- AÑADIR 1: Importar cors
const {
  WebpayPlus,
  Options,
  IntegrationCommerceCodes,
  IntegrationApiKeys,
  Environment
} = require('transbank-sdk');

// URLs desde .env con defaults útiles
const RETURN_URL = process.env.RETURN_URL || 'http://localhost:3010/webpay/return';
const FINAL_URL  = process.env.FINAL_URL  || 'http://localhost:3000/src/resultado.html';

// URL de tu backend de Flask
const FLASK_BACKEND_URL = 'http://localhost:5000';

// Instancia de Webpay en integración
const tx = new WebpayPlus.Transaction(
  new Options(
    IntegrationCommerceCodes.WEBPAY_PLUS,
    IntegrationApiKeys.WEBPAY,
    Environment.Integration
  )
);

// --- ▼▼▼ CONFIGURACIÓN DE CORS ▼▼▼ ---
// Opciones de CORS para permitir solo tu frontend
const corsOptions = {
  origin: 'http://localhost:3000', // Permite solo peticiones desde tu frontend
  optionsSuccessStatus: 200
};
router.use(cors(corsOptions)); // <--- AÑADIR 2: Usar cors con opciones
// --- ▲▲▲ FIN CONFIGURACIÓN CORS ▲▲▲ ---



// Crear transacción
router.post('/create', async (req, res) => {
  try {
    // 'amount' y 'buyOrder' (id_pedido) ahora vienen desde carrito.js
    const { amount = 0, buyOrder, sessionId } = req.body;
    
    // VALIDACIÓN: buyOrder AHORA DEBE SER UN NÚMERO
    const buyOrderInt = parseInt(buyOrder, 10);
    if (!buyOrderInt || isNaN(buyOrderInt)) {
        return res.status(400).json({ error: 'buyOrder (id_pedido) inválido o faltante' });
    }

    const _sessionId = sessionId || 'USR-' + Date.now();
    const amountInt  = Math.round(Number(amount) || 0);

    if (!amountInt || amountInt <= 0) {
      return res.status(400).json({ error: 'Monto inválido' });
    }
    
    console.log(`Creando transacción Webpay: Orden=${buyOrderInt}, Session=${_sessionId}, Monto=${amountInt}, ReturnURL=${RETURN_URL}`);
    
    // Usamos el buyOrderInt (id_pedido)
    const response = await tx.create(buyOrderInt, _sessionId, amountInt, RETURN_URL);
    
    console.log('Respuesta de Webpay create:', response);
    res.json(response);
  } catch (e) {
    console.error('create error:', e?.response?.data || e.message || e);
    res.status(500).json({ error: 'Error creando transacción' });
  }
});

// CORS requiere que las rutas POST también respondan a OPTIONS
router.options('/return', cors(corsOptions)); 



// Return (acepta POST y GET) -> commit y redirige a la página de resultado
router.post('/return', handleReturn);
router.get('/return', handleReturn);

async function handleReturn(req, res) {
  // --- Logs para depuración ---
  console.log('\n--- Petición recibida en /webpay/return ---');
  console.log('Query Params (GET):', req.query);
  console.log('Body Params (POST):', req.body);
  // --- Fin Logs ---

  const token = req.body?.token_ws || req.query?.token_ws;
  const tbkToken = req.body?.TBK_TOKEN || req.query?.TBK_TOKEN;

  // Si fue aborto/cancelación o no llegó token_ws, redirige como "abortado"
  if (!token || tbkToken) {
    console.log(`Redirección por Aborto/Cancelación. TBK_TOKEN: ${tbkToken}`);
    const abortParams = new URLSearchParams({
      estado: 'abortado'
    }).toString();
    const redirectUrl = `${FINAL_URL}#${abortParams}`; // Usando HASH
    console.log('Redirigiendo a (abortado):', redirectUrl);
    return res.redirect(redirectUrl);
  }

  let result; // Declarar result aquí
  try {
    console.log('Intentando hacer commit con token_ws:', token);
    result = await tx.commit(token); // Guardar en la variable 'result'
    console.log('Resultado del commit de Transbank:', result);

    // --- ▼▼▼ PASO 3: Informar a app.py (Flask) ▼▼▼ ---
    try {
        console.log(`Enviando resultado a Flask (${FLASK_BACKEND_URL}/api/registrar-pago)...`);
        const responseFlask = await fetch(`${FLASK_BACKEND_URL}/api/registrar-pago`, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(result) // Enviar el objeto 'result' completo
        });
        
        const dataFlask = await responseFlask.json();
        
        if (!responseFlask.ok) {
            throw new Error(dataFlask.error || "Error en el servidor Flask");
        }
        
        console.log(`Pago ${dataFlask.id_pago} registrado en la DB principal.`);

    } catch (dbError) {
        console.error('¡ERROR CRÍTICO! El pago fue exitoso en Transbank pero falló al guardar en app.py:', dbError.message);
        // Continuar de todas formas para no confundir al usuario
    }
    // --- ▲▲▲ FIN PASO 3 ▲▲▲ ---

    // Normaliza estado legible para UI
    const estado =
      result?.status === 'AUTHORIZED'
        ? 'aprobado'
        : ['FAILED', 'REVERSED', 'NULLIFIED'].includes(result?.status)
          ? 'rechazado'
          : 'pendiente';
    console.log('Estado calculado:', estado);

    // Construye los parámetros para la URL final
    const q = new URLSearchParams({
      estado,
      buy_order: String(result?.buy_order ?? ''), // Sigue siendo el id_pedido
      amount: String(result?.amount ?? ''),
      authorization_code: String(result?.authorization_code ?? ''),
      payment_type_code: String(result?.payment_type_code ?? ''),
      installments_number: String(result?.installments_number ?? 0),
      last4: String(result?.card_detail?.card_number ?? ''),
      token_ws: token
    }).toString();

    const redirectUrl = `${FINAL_URL}#${q}`; // Usando HASH
    console.log('Redirigiendo a (éxito/rechazo):', redirectUrl);
    return res.redirect(redirectUrl);

  } catch (e) {
    // Si el commit de Transbank falla
    console.error('commit error (Transbank):', e?.response?.data || e.message || e);
    const errParams = new URLSearchParams({
      estado: 'error'
    }).toString();
    const redirectUrl = `${FINAL_URL}#${errParams}`;
    console.log('Redirigiendo a (error commit):', redirectUrl);
    
    return res.redirect(redirectUrl);
  }
}

// (opcional) endpoint de status por token
router.get('/status/:token', async (req, res) => {
  try {
    console.log('Consultando estado para token:', req.params.token);
    const status = await tx.status(req.params.token);
    console.log('Resultado de status:', status);
    return res.json({ ok: true, status });
  } catch (e) {
    console.error('status error:', e?.response?.data || e.message || e);
    return res.status(500).json({ ok: false, error: 'Error obteniendo status' });
  }
});

module.exports = router;
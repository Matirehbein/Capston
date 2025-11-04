const router = require('express').Router();
const {
  WebpayPlus,
  Options,
  IntegrationCommerceCodes,
  IntegrationApiKeys,
  Environment
} = require('transbank-sdk');

// URLs desde .env con defaults útiles
const RETURN_URL = process.env.RETURN_URL || 'http://localhost:3010/webpay/return';
// --- Asegúrate que FINAL_URL siga apuntando a .html ---
const FINAL_URL  = process.env.FINAL_URL  || 'http://localhost:3000/src/resultado.html';

// Instancia de Webpay en integración
const tx = new WebpayPlus.Transaction(
  new Options(
    IntegrationCommerceCodes.WEBPAY_PLUS,
    IntegrationApiKeys.WEBPAY,
    Environment.Integration
  )
);

// Crear transacción
router.post('/create', async (req, res) => {
  try {
    const { amount = 0, buyOrder, sessionId } = req.body;
    const _buyOrder  = buyOrder  || 'ORD-' + Date.now();
    const _sessionId = sessionId || 'USR-' + Date.now();
    const amountInt  = Math.round(Number(amount) || 0);

    if (!amountInt || amountInt <= 0) {
      return res.status(400).json({ error: 'Monto inválido' });
    }
    console.log(`Creando transacción Webpay: Orden=${_buyOrder}, Session=${_sessionId}, Monto=${amountInt}, ReturnURL=${RETURN_URL}`);
    const response = await tx.create(_buyOrder, _sessionId, amountInt, RETURN_URL);
    console.log('Respuesta de Webpay create:', response);
    res.json(response);
  } catch (e) {
    console.error('create error:', e?.response?.data || e.message || e);
    res.status(500).json({ error: 'Error creando transacción' });
  }
});

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
    console.log(`Redirección por Aborto/Cancelación o Falta de token_ws. TBK_TOKEN: ${tbkToken}`);
    const abortParams = new URLSearchParams({
      estado: 'abortado'
    }).toString();
    // --- ▼▼▼ CAMBIO: Usar '#' en lugar de '?' ▼▼▼ ---
    const redirectUrl = `${FINAL_URL}#${abortParams}`;
    // --- ▲▲▲ FIN CAMBIO ▲▲▲ ---
    console.log('Redirigiendo a (abortado):', redirectUrl);
    return res.redirect(redirectUrl);
  }

  try {
    console.log('Intentando hacer commit con token_ws:', token);
    const result = await tx.commit(token);
    console.log('Resultado del commit de Transbank:', result); // Log del resultado completo

    // Normaliza estado legible para UI
    const estado =
      result?.status === 'AUTHORIZED'
        ? 'aprobado'
        : ['FAILED', 'REVERSED', 'NULLIFIED'].includes(result?.status)
          ? 'rechazado'
          : 'pendiente';
    console.log('Estado calculado:', estado); // Log del estado

    // Construye los parámetros para la URL final
    const q = new URLSearchParams({
      estado,
      buy_order: String(result?.buy_order ?? ''),
      amount: String(result?.amount ?? ''),
      authorization_code: String(result?.authorization_code ?? ''),
      payment_type_code: String(result?.payment_type_code ?? ''),
      installments_number: String(result?.installments_number ?? 0),
      last4: String(result?.card_detail?.card_number ?? ''),
      token_ws: token
    }).toString();

    // --- ▼▼▼ CAMBIO: Usar '#' en lugar de '?' ▼▼▼ ---
    const redirectUrl = `${FINAL_URL}#${q}`;
    // --- ▲▲▲ FIN CAMBIO ▲▲▲ ---
    console.log('Redirigiendo a (éxito/rechazo):', redirectUrl); // ¡ESTA ES LA LÍNEA IMPORTANTE!

    return res.redirect(redirectUrl); // Redirige a resultado.html con los parámetros en el hash

  } catch (e) {
    console.error('commit error:', e?.response?.data || e.message || e); // Log del error en commit
    const errParams = new URLSearchParams({
      estado: 'error'
    }).toString();
     // --- ▼▼▼ CAMBIO: Usar '#' en lugar de '?' ▼▼▼ ---
    const redirectUrl = `${FINAL_URL}#${errParams}`;
     // --- ▲▲▲ FIN CAMBIO ▲▲▲ ---
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
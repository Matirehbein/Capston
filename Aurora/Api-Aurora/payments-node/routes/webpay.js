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

    const response = await tx.create(_buyOrder, _sessionId, amountInt, RETURN_URL);
    // { token, url }
    res.json(response);
  } catch (e) {
    console.error('create error:', e?.response?.data || e.message || e);
    res.status(500).json({ error: 'Error creando transacción' });
  }
});

// ... lo tuyo arriba igual ...

// Return (acepta POST y GET) -> commit y redirige a la página de resultado
router.post('/return', handleReturn);
router.get('/return', handleReturn);

async function handleReturn(req, res) {
  // Webpay puede enviar token_ws (éxito) o TBK_TOKEN (aborto/cancelación)
  const token = req.body?.token_ws || req.query?.token_ws;
  const tbkToken = req.body?.TBK_TOKEN || req.query?.TBK_TOKEN;

  // Si fue aborto/cancelación o no llegó token_ws, redirige como "abortado"
  if (!token || tbkToken) {
    const abortParams = new URLSearchParams({
      estado: 'abortado'
    }).toString();
    return res.redirect(`${FINAL_URL}?${abortParams}`);
  }

  try {
    const result = await tx.commit(token);

    // Normaliza estado legible para UI
    const estado =
      result?.status === 'AUTHORIZED'
        ? 'aprobado'
        : ['FAILED', 'REVERSED', 'NULLIFIED'].includes(result?.status)
          ? 'rechazado'
          : 'pendiente';

    // ¡OJO! Evita mandar datos sensibles. Puedes guardar todo en BD y que el front consulte.
    const q = new URLSearchParams({
      estado,                              // aprobado | rechazado | pendiente
      buy_order: String(result?.buy_order ?? ''),
      amount: String(result?.amount ?? ''),
      authorization_code: String(result?.authorization_code ?? ''),
      payment_type_code: String(result?.payment_type_code ?? ''),
      installments_number: String(result?.installments_number ?? 0),
      last4: String(result?.card_detail?.card_number ?? ''),
      token_ws: token                       // útil si luego consultas /status/:token
    }).toString();

    return res.redirect(`${FINAL_URL}?${q}`);
  } catch (e) {
    console.error('commit error:', e?.response?.data || e.message || e);
    const errParams = new URLSearchParams({
      estado: 'error'
    }).toString();
    return res.redirect(`${FINAL_URL}?${errParams}`);
  }
}

// (opcional) endpoint de status por token para que el front valide/complete datos
router.get('/status/:token', async (req, res) => {
  try {
    const status = await tx.status(req.params.token);
    return res.json({ ok: true, status });
  } catch (e) {
    console.error('status error:', e?.response?.data || e.message || e);
    return res.status(500).json({ ok: false, error: 'Error obteniendo status' });
  }
});

module.exports = router;

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
const FINAL_URL  = process.env.FINAL_URL  || 'http://localhost:3000/src/carrito.html';

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

// Return (acepta POST y GET) -> commit y redirige al carrito
router.post('/return', handleReturn);
router.get('/return', handleReturn);

async function handleReturn(req, res) {
  const token = req.body?.token_ws || req.query?.token_ws;
  if (!token) return res.status(400).send('token_ws faltante');

  try {
    const result = await tx.commit(token);
    const success = result?.status === 'AUTHORIZED';

    const q = new URLSearchParams({
      success: success ? 'true' : 'false',
      amount: String(result?.amount ?? ''),
      authorization_code: String(result?.authorization_code ?? ''),
      buy_order: String(result?.buy_order ?? '')
    }).toString();

    return res.redirect(`${FINAL_URL}?${q}`);
  } catch (e) {
    console.error('commit error:', e?.response?.data || e.message || e);
    return res.redirect(`${FINAL_URL}?success=false&error=commit_failed`);
  }
}

// (opcional) página de debug
router.get('/finish', (req, res) => {
  res.send(`
    <h2>Resultado Webpay (debug)</h2>
    <pre>${JSON.stringify(req.query, null, 2)}</pre>
    <a href="/">Volver</a>
  `);
});

module.exports = router;

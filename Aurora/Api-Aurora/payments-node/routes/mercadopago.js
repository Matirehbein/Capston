const express = require('express');
const { MercadoPagoConfig, Preference } = require('mercadopago');

const router = express.Router();

const client = new MercadoPagoConfig({
  accessToken: process.env.MP_ACCESS_TOKEN
});

// URL a la que el usuario vuelve manualmente si presiona "Volver al sitio"
const FRONT_RESULT = process.env.FRONT_RESULT_URL || 'http://localhost:3000/resultado.html';

router.post('/create_preference', async (req, res) => {
  try {
    const { items: bodyItems = [], amount } = req.body || {};

    // Generar ítems dinámicos
    const mpItems =
      Array.isArray(bodyItems) && bodyItems.length > 0
        ? bodyItems.map(it => ({
            title: String(it.title || 'Producto'),
            quantity: Number(it.quantity || 1),
            unit_price: Math.round(Number(it.unit_price || 0)),
            currency_id: it.currency_id || 'CLP',
            picture_url: it.picture_url
          }))
        : Number.isFinite(Number(amount)) && Number(amount) > 0
          ? [{ title: 'Compra Aurora', quantity: 1, unit_price: Math.round(Number(amount)), currency_id: 'CLP' }]
          : [{ title: 'Producto de prueba', quantity: 1, unit_price: 2000, currency_id: 'CLP' }];

    const preference = new Preference(client);

    const r = await preference.create({
      body: {
        items: mpItems,
        back_urls: {
          success: FRONT_RESULT,
          failure: FRONT_RESULT,
          pending: FRONT_RESULT
        }
        // ⚠️ No usamos auto_return
      }
    });

    res.json({
      id: r.id,
      init_point: r.init_point,
      sandbox_init_point: r.sandbox_init_point
    });

  } catch (err) {
    console.error('❌ Error al crear preferencia:', err?.response?.data || err);
    res.status(500).json({
      error: 'mp_create_preference_failed',
      detail: err?.response?.data || err?.message
    });
  }
});

module.exports = router;

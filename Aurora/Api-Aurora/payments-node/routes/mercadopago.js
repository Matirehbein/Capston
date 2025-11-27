const express = require('express');
const { MercadoPagoConfig, Preference } = require('mercadopago');

const router = express.Router();

const client = new MercadoPagoConfig({
  accessToken: process.env.MP_ACCESS_TOKEN,
});

// Tu URL de ngrok (¡está correcta!)
// 👇 Quitamos el .html para evitar que el servidor haga redirecciones y pierda los datos
const FINAL_URL = 'https://janiece-unincited-openhandedly.ngrok-free.devo';
const looksUrl = u => /^https?:\/\//i.test(u);

router.post('/create', async (req, res) => {
  try {
    const { items: inItems, external_reference: externalReference } = req.body;

    if (!Array.isArray(inItems) || !inItems.length) {
        return res.status(400).json({ error: 'items_required' });
    }
    
    if (!externalReference) {
        return res.status(400).json({ error: 'external_reference (ID Pedido) es requerida' });
    }

    const items = inItems.map((it, i) => ({
      id: String(it.id ?? it.sku ?? i + 1),
      title: String(it.title ?? it.titulo ?? it.name ?? 'Producto'),
      quantity: Math.max(1, Number(it.quantity ?? it.qty ?? 1) || 1),
      unit_price: Math.max(
        1,
        Math.round(
          Number(String(it.unit_price ?? it.precio ?? it.price ?? 0).replace(/[^\d.-]/g, '')) || 0
        )
      ),
      currency_id: it.currency_id || 'CLP',
    })).filter(x => x.quantity >= 1 && x.unit_price >= 1);

    if (!items.length) {
      return res.status(400).json({ error: 'items_invalid', details: 'unit_price y quantity >= 1' });
    }

    if (!looksUrl(FINAL_URL)) {
      return res.status(500).json({ error: 'config_error', details: 'FINAL_URL inválida (debe ser https)' });
    }

    const body = {
      items,
      back_urls: { success: FINAL_URL, failure: FINAL_URL, pending: FINAL_URL },
      auto_return: 'approved',
      external_reference: String(externalReference),
    };


    // Logs de verificación (deben aparecer en la consola del server)
    console.log('FINAL_URL →', FINAL_URL);
    console.log('Body MP →', JSON.stringify(body, null, 2));

    const preference = new Preference(client);
    
    // --- ▼▼▼ ¡ESTA ES LA CORRECCIÓN! ▼▼▼ ---
    // La nueva versión del SDK SÍ espera que el objeto 'body' esté envuelto.
    const mp = await preference.create({ body });
    // --- ▲▲▲ FIN CORRECCIÓN ▲▲▲ ---

    return res.json({
      id: mp.id,
      init_point: mp.init_point,
      sandbox_init_point: mp.sandbox_init_point,
    });
  } catch (e) {
    console.error('MP create error →', { status: e?.status, message: e?.message, cause: e?.cause });
    return res.status(e?.status || 500).json({
      error: 'mp_create_failed',
      status: e?.status || 500,
      message: e?.message || 'unknown',
      cause: e?.cause || null,
    });
  }
});

module.exports = router;
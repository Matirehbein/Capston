const express = require('express');
const cors = require('cors');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 3010;

app.use(cors());
app.use(express.json());

// RUTAS
const webpayRoutes = require('./routes/webpay');           // <- tu ruta existente
const mercadopagoRoutes = require('./routes/mercadopago'); // <- la que creamos abajo
app.use('/webpay', webpayRoutes);
app.use('/mercadopago', mercadopagoRoutes);

// Página base (opcional)
app.get('/', (_req, res) => res.send('Servidor de pagos activo ✅ (Webpay + MP)'));

// Healthcheck útil
app.get('/healthz', (_req, res) => {
  const mask = v => (v ? v.slice(0, 10) + '...' : 'MISSING');
  res.json({
    MP_ACCESS_TOKEN: mask(process.env.MP_ACCESS_TOKEN),
    FRONT_SUCCESS_URL: process.env.FRONT_SUCCESS_URL,
    FRONT_FAILURE_URL: process.env.FRONT_FAILURE_URL,
    FRONT_PENDING_URL: process.env.FRONT_PENDING_URL,
  });
});

app.listen(PORT, () => {
  console.log(`✓ Pagos en http://localhost:${PORT}`);
});

// server.js
require('dotenv').config();
const express = require('express');
const cors = require('cors');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3010;

app.use(cors());
app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

// === Tus rutas existentes ===
const webpayRoutes = require('./routes/webpay');
app.use('/webpay', webpayRoutes);

// === NUEVA RUTA MERCADO PAGO ===
const mpRoutes = require('./routes/mercadopago');
app.use('/api/mercadopago', mpRoutes);


// (opcional)
app.get('/', (_req, res) => res.send('Servidor activo (Webpay + MP) ✅'));

app.listen(PORT, () => {
  console.log(`Pagos activos en http://localhost:${PORT}`);
});

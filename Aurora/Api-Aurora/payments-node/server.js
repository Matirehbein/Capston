// server.js
require('dotenv').config();
const express = require('express');
const cors = require('cors');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3010;

// --- ▼▼▼ CORRECCIÓN CRÍTICA DE CORS ▼▼▼ ---
// Esto permite que el frontend (localhost:3000) envíe cookies/credenciales
// sin que el navegador bloquee la respuesta.
app.use(cors({
  origin: ['http://localhost:3000', 'http://127.0.0.1:3000'], // Permite ambos orígenes locales
  credentials: true,
  methods: ['GET', 'POST', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization']
}));
// --- ▲▲▲ FIN CORRECCIÓN ▲▲▲ ---

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
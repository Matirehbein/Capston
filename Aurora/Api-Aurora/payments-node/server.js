const express = require('express');
const dotenv  = require('dotenv');
const cors    = require('cors');

dotenv.config();
const app = express();

app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true })); // necesario para token_ws (POST)
app.use('/webpay', require('./routes/webpay'));


app.get('/health', (_req, res) => res.json({ ok: true }));

const PORT = process.env.PORT || 3010;
app.listen(PORT, () => console.log(`Webpay Node corriendo en http://localhost:${PORT}`));

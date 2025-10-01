const axios = require('axios');
const {Pool} = require('pg');

// Configuración de conexión
const pool = new Pool({
  host: 'localhost',
  user: 'postgres',
  password: 'duoc',   // tu contraseña
  database: 'aurora', // tu base de datos
  port: 5432          // número (no string)
});

// Probar la conexión
pool.connect()
    .then(client => {
    console.log("✅ Conectado a PostgreSQL");
    client.release();   
    })
.catch(err => console.error("❌ Error al conectar a PostgreSQL:", err.stack));
const axios = require('axios');
const {Pool} = requier('pg');

const pool = new Pool({
    host: 'localhost',
    user: 'postgres',
    password: 'duoc',
    database: 'aurora',
    port: '5432'
});
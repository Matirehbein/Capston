CREATE DATABASE aurora;

-- Elimina índices opcionales
DROP INDEX IF EXISTS idx_conversacion_usuario;
DROP INDEX IF EXISTS idx_ticket_conversacion;
DROP INDEX IF EXISTS uniq_ticket_activo_por_prioridad;
DROP INDEX IF EXISTS idx_pedido_usuario;
DROP INDEX IF EXISTS idx_pedido_cupon;
DROP INDEX IF EXISTS idx_oferta_producto_oferta;
DROP INDEX IF EXISTS idx_oferta_producto_producto;
DROP INDEX IF EXISTS idx_variacion_producto_prod;
DROP INDEX IF EXISTS idx_inventario_variacion;
DROP INDEX IF EXISTS idx_inventario_sucursal;
DROP INDEX IF EXISTS idx_detalle_pedido_pedido;
DROP INDEX IF EXISTS idx_detalle_pedido_variacion;

-- Elimina foreign keys
ALTER TABLE IF EXISTS conversacion        DROP CONSTRAINT IF EXISTS conversacion_usuario_fk;
ALTER TABLE IF EXISTS ticket              DROP CONSTRAINT IF EXISTS ticket_conversacion_fk;
ALTER TABLE IF EXISTS pedido              DROP CONSTRAINT IF EXISTS pedido_usuario_fk;
ALTER TABLE IF EXISTS pedido              DROP CONSTRAINT IF EXISTS pedido_cupon_fk;
ALTER TABLE IF EXISTS oferta_producto     DROP CONSTRAINT IF EXISTS oferta_fk;
ALTER TABLE IF EXISTS oferta_producto     DROP CONSTRAINT IF EXISTS producto_fk;
ALTER TABLE IF EXISTS variacion_producto  DROP CONSTRAINT IF EXISTS variacion_producto_fk;
ALTER TABLE IF EXISTS inventario_sucursal DROP CONSTRAINT IF EXISTS inventario_sucursal_sucursal_fk;
ALTER TABLE IF EXISTS inventario_sucursal DROP CONSTRAINT IF EXISTS inventario_sucursal_variacion_fk;
ALTER TABLE IF EXISTS detalle_pedido      DROP CONSTRAINT IF EXISTS detalle_pedido_pedido_fk;
ALTER TABLE IF EXISTS detalle_pedido      DROP CONSTRAINT IF EXISTS detalle_pedido_variacion_fk;

-- Elimina tablas (de menor a mayor dependencia)
DROP TABLE IF EXISTS detalle_pedido CASCADE;
DROP TABLE IF EXISTS inventario_sucursal CASCADE;
DROP TABLE IF EXISTS variacion_producto CASCADE;
DROP TABLE IF EXISTS oferta_producto CASCADE;
DROP TABLE IF EXISTS producto CASCADE;
DROP TABLE IF EXISTS oferta CASCADE;
DROP TABLE IF EXISTS sucursal CASCADE;
DROP TABLE IF EXISTS pedido CASCADE;
DROP TABLE IF EXISTS cupon CASCADE;
DROP TABLE IF EXISTS ticket CASCADE;
DROP TABLE IF EXISTS conversacion CASCADE;
DROP TABLE IF EXISTS usuario CASCADE;

-- Creación de tablas
CREATE TABLE public.usuario (
    id_usuario integer NOT NULL,
    nombre_usuario character varying(100) NOT NULL,
    email_usuario character varying(150) NOT NULL,
    rol_usuario character varying(20),
    password character varying(255) NOT NULL,
    creado_en timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    apellido_paterno character varying(100) DEFAULT 'SIN APELLIDO'::character varying NOT NULL,
    apellido_materno character varying(100) DEFAULT 'SIN APELLIDO'::character varying NOT NULL,
    calle character varying(150),
    numero_calle character varying(10),
    region character varying(100),
    ciudad character varying(100),
    comuna character varying(100),
    telefono character varying(20),
    CONSTRAINT usuario_rol_usuario_check CHECK (((rol_usuario)::text = ANY ((ARRAY['cliente'::character varying, 'admin'::character varying, 'soporte'::character varying])::text[])))
);


CREATE TABLE conversacion (
  id_conversacion SERIAL PRIMARY KEY,
  mensajes_json JSONB NOT NULL,
  motivo VARCHAR(150),
  csat INT CHECK (csat BETWEEN 1 AND 5),
  creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE ticket (
  id_ticket SERIAL PRIMARY KEY,
  resumen VARCHAR(200) NOT NULL,
  prioridad VARCHAR(20) CHECK (prioridad IN ('baja', 'media', 'alta', 'critica')),
  estado VARCHAR(20) CHECK (estado IN ('abierto', 'en_proceso', 'resuelto', 'cerrado')),
  creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE cupon (
  id_cupon SERIAL PRIMARY KEY,
  codigo_cupon VARCHAR(50) UNIQUE NOT NULL,
  descuento_pct_cupon NUMERIC(5,2),
  valor_fijo NUMERIC(10,2),
  min_compra NUMERIC(10,2),
  usos_max INT NOT NULL,
  usos_hechos INT DEFAULT 0,
  reglas_json JSONB,
  vigente_bool BOOLEAN DEFAULT TRUE,
  fecha_inicio DATE,
  fecha_fin DATE,
  CHECK (fecha_inicio <= fecha_fin)
);

CREATE TABLE pedido (
  id_pedido SERIAL PRIMARY KEY,
  estado_pedido VARCHAR(20) CHECK (estado_pedido IN ('creado','pagado','preparado','enviado','entregado')),
  creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE sucursal (
  id_sucursal SERIAL PRIMARY KEY,
  nombre_sucursal VARCHAR(100) NOT NULL,
  region_sucursal VARCHAR(100) NOT NULL,
  comuna_sucursal VARCHAR(100) NOT NULL,
  direccion_sucursal VARCHAR(200) NOT NULL,
  latitud_sucursal NUMERIC(9,6),
  longitud_sucursal NUMERIC(9,6),
  horario_json JSONB,
  telefono_sucursal VARCHAR(20)
);

CREATE TABLE oferta (
  id_oferta SERIAL PRIMARY KEY,
  titulo VARCHAR(150) NOT NULL,
  descripcion TEXT,
  descuento_pct NUMERIC(5,2) NOT NULL,
  fecha_inicio DATE NOT NULL,
  fecha_fin DATE NOT NULL,
  vigente_bool BOOLEAN DEFAULT TRUE,
  CHECK (fecha_inicio <= fecha_fin),
  CHECK (descuento_pct > 0 AND descuento_pct <= 100)
);

CREATE TABLE producto (
  id_producto SERIAL PRIMARY KEY,
  sku VARCHAR(50) UNIQUE NOT NULL,
  nombre_producto VARCHAR(150) NOT NULL,
  descripcion_producto TEXT,
  categoria_producto VARCHAR(100),
  precio_producto NUMERIC(10,2) NOT NULL,
  imagen_url TEXT
);

CREATE TABLE oferta_producto (
  id_oferta INT NOT NULL,
  id_producto INT NOT NULL,
  PRIMARY KEY (id_oferta, id_producto)
);

CREATE TABLE variacion_producto (
  id_variacion SERIAL PRIMARY KEY,
  talla VARCHAR(20),
  color VARCHAR(50),
  sku_variacion VARCHAR(50) UNIQUE
);

CREATE TABLE inventario_sucursal (
  id_inventario SERIAL PRIMARY KEY,
  stock INT NOT NULL DEFAULT 0
);

CREATE TABLE detalle_pedido (
  id_detalle SERIAL PRIMARY KEY,
  cantidad INT NOT NULL CHECK (cantidad > 0),
  precio_unitario NUMERIC(10,2) NOT NULL CHECK (precio_unitario >= 0)
);

--Generacion de fg keys
ALTER TABLE conversacion
  ADD COLUMN id_usuario INT;

ALTER TABLE conversacion
  ADD CONSTRAINT conversacion_usuario_fk
  FOREIGN KEY (id_usuario) REFERENCES usuario(id_usuario) ON DELETE SET NULL;

ALTER TABLE ticket
  ADD COLUMN id_conversacion INT NOT NULL;

ALTER TABLE ticket
  ADD CONSTRAINT ticket_conversacion_fk
  FOREIGN KEY (id_conversacion) REFERENCES conversacion(id_conversacion) ON DELETE CASCADE;

ALTER TABLE cupon
  ADD CONSTRAINT cupon_tipo_ck
  CHECK (
    (descuento_pct_cupon IS NOT NULL AND valor_fijo IS NULL)
    OR (descuento_pct_cupon IS NULL AND valor_fijo IS NOT NULL)
  );

ALTER TABLE cupon
  ADD CONSTRAINT cupon_usos_ck
  CHECK (usos_max >= 0 AND usos_hechos >= 0);

ALTER TABLE pedido
  ADD COLUMN id_usuario INT NOT NULL,
  ADD COLUMN id_cupon   INT;

ALTER TABLE pedido
  ADD CONSTRAINT pedido_usuario_fk
  FOREIGN KEY (id_usuario) REFERENCES usuario(id_usuario) ON DELETE RESTRICT;

ALTER TABLE pedido
  ADD CONSTRAINT pedido_cupon_fk
  FOREIGN KEY (id_cupon) REFERENCES cupon(id_cupon) ON DELETE SET NULL;

ALTER TABLE oferta_producto
  ADD CONSTRAINT oferta_fk   FOREIGN KEY (id_oferta)   REFERENCES oferta(id_oferta)   ON DELETE CASCADE,
  ADD CONSTRAINT producto_fk FOREIGN KEY (id_producto) REFERENCES producto(id_producto) ON DELETE CASCADE;

ALTER TABLE variacion_producto
  ADD COLUMN id_producto INT NOT NULL;

ALTER TABLE variacion_producto
  ADD CONSTRAINT variacion_producto_fk
  FOREIGN KEY (id_producto) REFERENCES producto(id_producto) ON DELETE CASCADE;

ALTER TABLE inventario_sucursal
  ADD COLUMN id_sucursal  INT NOT NULL,
  ADD COLUMN id_variacion INT NOT NULL;

ALTER TABLE inventario_sucursal
  ADD CONSTRAINT inventario_sucursal_sucursal_fk
  FOREIGN KEY (id_sucursal)  REFERENCES sucursal(id_sucursal) ON DELETE CASCADE;

ALTER TABLE inventario_sucursal
  ADD CONSTRAINT inventario_sucursal_variacion_fk
  FOREIGN KEY (id_variacion) REFERENCES variacion_producto(id_variacion) ON DELETE CASCADE;
ALTER TABLE inventario_sucursal
  ADD CONSTRAINT inventario_sucursal_unq UNIQUE (id_sucursal, id_variacion);

ALTER TABLE detalle_pedido
  ADD COLUMN id_pedido    INT NOT NULL,
  ADD COLUMN id_variacion INT NOT NULL;

ALTER TABLE detalle_pedido
  ADD CONSTRAINT detalle_pedido_pedido_fk
  FOREIGN KEY (id_pedido)    REFERENCES pedido(id_pedido) ON DELETE CASCADE;
ALTER TABLE detalle_pedido
  ADD CONSTRAINT detalle_pedido_variacion_fk
  FOREIGN KEY (id_variacion) REFERENCES variacion_producto(id_variacion) ON DELETE RESTRICT;

-- Creación de índices
CREATE INDEX idx_conversacion_usuario        ON conversacion(id_usuario);
CREATE INDEX IF NOT EXISTS idx_pedido_usuario ON pedido(id_usuario);
CREATE INDEX IF NOT EXISTS idx_pedido_cupon   ON pedido(id_cupon);
CREATE INDEX idx_oferta_producto_oferta      ON oferta_producto(id_oferta);
CREATE INDEX idx_oferta_producto_producto    ON oferta_producto(id_producto);
CREATE INDEX idx_ticket_conversacion         ON ticket(id_conversacion);
CREATE UNIQUE INDEX IF NOT EXISTS uniq_ticket_activo_por_prioridad
  ON ticket(id_conversacion, prioridad)
  WHERE estado IN ('abierto','en_proceso');
CREATE INDEX idx_variacion_producto_prod     ON variacion_producto(id_producto);
CREATE INDEX idx_inventario_sucursal         ON inventario_sucursal(id_sucursal);
CREATE INDEX idx_inventario_variacion        ON inventario_sucursal(id_variacion);


-- SQLBook: Code
-- DROP SCHEMA ml;

CREATE SCHEMA ml AUTHORIZATION dba_suseso;

-- DROP SEQUENCE ml.especialidad_profesional_id_especialidad_profesional_seq;

CREATE SEQUENCE ml.especialidad_profesional_id_especialidad_profesional_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 2147483647
	START 1
	CACHE 1
	NO CYCLE;

-- Permissions

ALTER SEQUENCE ml.especialidad_profesional_id_especialidad_profesional_seq OWNER TO postgres;
GRANT ALL ON SEQUENCE ml.especialidad_profesional_id_especialidad_profesional_seq TO postgres;

-- DROP SEQUENCE ml.especialidad_profesional_medi_id_especialidad_profesional_m_seq;

CREATE SEQUENCE ml.especialidad_profesional_medi_id_especialidad_profesional_m_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 2147483647
	START 1
	CACHE 1
	NO CYCLE;

-- Permissions

ALTER SEQUENCE ml.especialidad_profesional_medi_id_especialidad_profesional_m_seq OWNER TO postgres;
GRANT ALL ON SEQUENCE ml.especialidad_profesional_medi_id_especialidad_profesional_m_seq TO postgres;

-- DROP SEQUENCE ml.licencias_id_licencias_seq;

CREATE SEQUENCE ml.licencias_id_licencias_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 2147483647
	START 1
	CACHE 1
	NO CYCLE;

-- Permissions

ALTER SEQUENCE ml.licencias_id_licencias_seq OWNER TO postgres;
GRANT ALL ON SEQUENCE ml.licencias_id_licencias_seq TO postgres;

-- DROP SEQUENCE ml.profesionalidad_id_profesionalidad_seq;

CREATE SEQUENCE ml.profesionalidad_id_profesionalidad_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 2147483647
	START 1
	CACHE 1
	NO CYCLE;

-- Permissions

ALTER SEQUENCE ml.profesionalidad_id_profesionalidad_seq OWNER TO postgres;
GRANT ALL ON SEQUENCE ml.profesionalidad_id_profesionalidad_seq TO postgres;
-- ml.especialidad_profesional definition

-- Drop table

-- DROP TABLE ml.especialidad_profesional;

CREATE TABLE ml.especialidad_profesional (
	id_especialidad_profesional serial4 NOT NULL,
	descripcion_especialidad_profesional varchar(255) NULL,
	CONSTRAINT especialidad_profesional_descripcion_especialidad_profesion_key UNIQUE (descripcion_especialidad_profesional),
	CONSTRAINT especialidad_profesional_pkey PRIMARY KEY (id_especialidad_profesional)
);

-- Permissions

ALTER TABLE ml.especialidad_profesional OWNER TO postgres;
GRANT ALL ON TABLE ml.especialidad_profesional TO postgres;
GRANT SELECT ON TABLE ml.especialidad_profesional TO consultor;


-- ml.medicos definition

-- Drop table

-- DROP TABLE ml.medicos;

CREATE TABLE ml.medicos (
	rut_medico varchar(128) NOT NULL,
	CONSTRAINT medicos_pkey PRIMARY KEY (rut_medico)
);

-- Permissions

ALTER TABLE ml.medicos OWNER TO postgres;
GRANT ALL ON TABLE ml.medicos TO postgres;
GRANT SELECT ON TABLE ml.medicos TO consultor;


-- ml.profesionalidad definition

-- Drop table

-- DROP TABLE ml.profesionalidad;

CREATE TABLE ml.profesionalidad (
	id_profesionalidad serial4 NOT NULL,
	descripcion_profesionalidad varchar NOT NULL,
	CONSTRAINT profesionalidad_descripcion_profesionalidad_key UNIQUE (descripcion_profesionalidad),
	CONSTRAINT profesionalidad_pkey PRIMARY KEY (id_profesionalidad)
);

-- Permissions

ALTER TABLE ml.profesionalidad OWNER TO postgres;
GRANT ALL ON TABLE ml.profesionalidad TO postgres;
GRANT SELECT ON TABLE ml.profesionalidad TO consultor;


-- ml.propensity_score definition

-- Drop table

-- DROP TABLE ml.propensity_score;

CREATE TABLE ml.propensity_score (
	id_propensity_score int8 NULL,
	id_lic varchar(128) NULL,
	folio varchar NULL,
	rn int4 NULL,
	rn2 int4 NULL,
	frecuencia_mensual float4 NULL,
	frecuencia_semanal float4 NULL,
	otorgados_mensual float4 NULL,
	otorgados_semanal float4 NULL,
	ml float4 NULL,
	score float4 NULL
);

-- Permissions

ALTER TABLE ml.propensity_score OWNER TO postgres;
GRANT ALL ON TABLE ml.propensity_score TO postgres;


-- ml.propensity_score_bak definition

-- Drop table

-- DROP TABLE ml.propensity_score_bak;

CREATE TABLE ml.propensity_score_bak (
	id_propensity_score int8 NULL,
	id_lic varchar(128) NULL,
	folio varchar NULL,
	rn int4 NULL,
	rn2 int4 NULL,
	frecuencia_mensual float4 NULL,
	frecuencia_semanal float4 NULL,
	otorgados_mensual float4 NULL,
	otorgados_semanal float4 NULL,
	ml float4 NULL,
	score float4 NULL
);

-- Permissions

ALTER TABLE ml.propensity_score_bak OWNER TO postgres;
GRANT ALL ON TABLE ml.propensity_score_bak TO postgres;
GRANT SELECT ON TABLE ml.propensity_score_bak TO consultor;


-- ml.especialidad_profesional_medicos definition

-- Drop table

-- DROP TABLE ml.especialidad_profesional_medicos;

CREATE TABLE ml.especialidad_profesional_medicos (
	id_especialidad_profesional_medicos int4 DEFAULT nextval('ml.especialidad_profesional_medi_id_especialidad_profesional_m_seq'::regclass) NOT NULL,
	rut_medico varchar(128) NOT NULL,
	id_especialidad_profesional int4 NULL,
	CONSTRAINT especialidad_profesional_medicos_pkey PRIMARY KEY (id_especialidad_profesional_medicos, rut_medico),
	CONSTRAINT unique_id_especialidad_profesional_medicos UNIQUE (id_especialidad_profesional_medicos),
	CONSTRAINT fk_id_especialidad_profesional FOREIGN KEY (id_especialidad_profesional) REFERENCES ml.especialidad_profesional(id_especialidad_profesional),
	CONSTRAINT fk_rut_medico FOREIGN KEY (rut_medico) REFERENCES ml.medicos(rut_medico)
);
CREATE INDEX idx_epm_id_especialidad ON ml.especialidad_profesional_medicos USING btree (id_especialidad_profesional);

-- Permissions

ALTER TABLE ml.especialidad_profesional_medicos OWNER TO postgres;
GRANT ALL ON TABLE ml.especialidad_profesional_medicos TO postgres;
GRANT SELECT ON TABLE ml.especialidad_profesional_medicos TO consultor;


-- ml.licencias definition

-- Drop table

-- DROP TABLE ml.licencias;

CREATE TABLE ml.licencias (
	id_licencias serial4 NOT NULL,
	id_lic varchar(128) NULL,
	operador varchar NULL,
	ccaf varchar NULL,
	entidad_pagadora varchar NULL,
	folio varchar NULL,
	fecha_emision date NULL,
	empleador_adscrito int4 NULL,
	codigo_interno_prestador int4 NULL,
	comuna_prestador varchar NULL,
	fecha_ultimo_estado date NULL,
	ultimo_estado int4 NULL,
	rut_trabajador varchar(128) NULL,
	sexo_trabajador varchar NULL,
	edad_trabajador float4 NULL,
	tipo_reposo varchar NULL,
	dias_reposo int4 NULL,
	fecha_inicio_reposo date NULL,
	comuna_reposo varchar NULL,
	tipo_licencia int4 NULL,
	rut_medico varchar(128) NULL,
	tipo_licencia_pronunciamiento float4 NULL,
	codigo_continuacion_pronunciamiento float4 NULL,
	dias_autorizados_pronunciamiento float4 NULL,
	codigo_diagnostico_pronunciamiento varchar NULL,
	codigo_autorizacion_pronunciamiento float4 NULL,
	causa_rechazo_pronunciamiento varchar NULL,
	tipo_reposo_pronunciamiento varchar NULL,
	derecho_a_subsidio_pronunciamiento varchar NULL,
	rut_empleador varchar(128) NULL,
	calidad_trabajador varchar(64) NULL,
	actividad_laboral_trabajador int4 NULL,
	ocupacion int4 NULL,
	entidad_pagadora_zona_c varchar NULL,
	fecha_recepcion_empleador varchar NULL,
	regimen_previsional int4 NULL,
	entidad_pagadora_subsidio varchar NULL,
	comuna_laboral varchar NULL,
	comuna_uso_compin varchar NULL,
	cantidad_de_pronunciamientos int4 NULL,
	cantidad_de_zonas_d int4 NULL,
	secuencia_estados varchar NULL,
	cod_diagnostico_principal varchar NULL,
	cod_diagnostico_secundario varchar NULL,
	periodo varchar NULL,
	CONSTRAINT licencias_pkey PRIMARY KEY (id_licencias),
	CONSTRAINT unique_folio UNIQUE (folio),
	CONSTRAINT unique_id_lic UNIQUE (id_lic),
	CONSTRAINT fk_licencias_rut_medico FOREIGN KEY (rut_medico) REFERENCES ml.medicos(rut_medico)
);

-- Permissions

ALTER TABLE ml.licencias OWNER TO postgres;
GRANT ALL ON TABLE ml.licencias TO postgres;
GRANT SELECT ON TABLE ml.licencias TO consultor;


-- ml.profesionalidad_medicos definition

-- Drop table

-- DROP TABLE ml.profesionalidad_medicos;

CREATE TABLE ml.profesionalidad_medicos (
	id_profesionalidad int4 NOT NULL,
	rut_medico varchar(128) NOT NULL,
	CONSTRAINT profesionalidad_medicos_pkey PRIMARY KEY (id_profesionalidad, rut_medico),
	CONSTRAINT profesionalidad_medicos_id_profesionalidad_fkey FOREIGN KEY (id_profesionalidad) REFERENCES ml.profesionalidad(id_profesionalidad),
	CONSTRAINT profesionalidad_medicos_rut_medico_fkey FOREIGN KEY (rut_medico) REFERENCES ml.medicos(rut_medico)
);

-- Permissions

ALTER TABLE ml.profesionalidad_medicos OWNER TO postgres;
GRANT ALL ON TABLE ml.profesionalidad_medicos TO postgres;
GRANT SELECT ON TABLE ml.profesionalidad_medicos TO consultor;




-- Permissions

GRANT ALL ON SCHEMA ml TO dba_suseso;
GRANT USAGE ON SCHEMA ml TO consultor;
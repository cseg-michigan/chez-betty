CREATE TABLE ephemera (
	id SERIAL,
	"timestamp" timestamp without time zone NOT NULL,
	name character varying(255) NOT NULL,
	value TEXT NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (name)
);

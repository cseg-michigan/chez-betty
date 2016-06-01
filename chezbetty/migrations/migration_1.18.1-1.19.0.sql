/* WARN: This migration drops all old requests since the storage format changed significantly */
COPY requests TO '/tmp/cb_old_requests.csv' DELIMITER ',' CSV HEADER;

CREATE TABLE requests_pre_v1_19 AS SELECT * FROM requests;

DELETE FROM requests;
ALTER TABLE requests ADD COLUMN vendor_id INTEGER NOT NULL;
ALTER TABLE requests ADD CONSTRAINT vendor_id FOREIGN KEY(vendor_id) REFERENCES vendors(id) MATCH FULL;
ALTER TABLE requests ADD COLUMN vendor_url TEXT;

ALTER TABLE vendors ADD COLUMN product_urls BOOLEAN;
UPDATE vendors SET product_urls=True WHERE name='Amazon';
UPDATE vendors SET product_urls=True WHERE name='TalDepot';

CREATE TABLE request_posts (
	id SERIAL,
	"timestamp" timestamp without time zone NOT NULL,
	request_id INTEGER NOT NULL,
	user_id INTEGER NOT NULL,
	post TEXT,
	staff_post BOOLEAN NOT NULL DEFAULT FALSE,
	deleted BOOLEAN NOT NULL DEFAULT FALSE
);
ALTER TABLE request_posts ADD CONSTRAINT request_id FOREIGN KEY(request_id) REFERENCES requests(id) MATCH FULL;
ALTER TABLE request_posts ADD CONSTRAINT user_id FOREIGN KEY(user_id) REFERENCES users(id) MATCH FULL;

/* ALTER TABLE requests ADD COLUMN response TEXT; */


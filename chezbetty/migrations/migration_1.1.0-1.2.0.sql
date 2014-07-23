
CREATE TABLE boxes (
	id INTEGER NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	barcode VARCHAR(255), 
	wholesale NUMERIC NOT NULL, 
	enabled BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (barcode), 
	CHECK (enabled IN (0, 1))
);

CREATE TABLE box_items (
	id INTEGER NOT NULL, 
	box_id INTEGER NOT NULL, 
	item_id INTEGER NOT NULL, 
	quantity INTEGER NOT NULL, 
	enabled BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(box_id) REFERENCES boxes (id), 
	FOREIGN KEY(item_id) REFERENCES items (id), 
	CHECK (enabled IN (0, 1))
);

CREATE TABLE box_vendors (
	id INTEGER NOT NULL, 
	vendor_id INTEGER NOT NULL, 
	box_id INTEGER NOT NULL, 
	item_number VARCHAR(255) NOT NULL, 
	enabled BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(vendor_id) REFERENCES vendors (id), 
	FOREIGN KEY(box_id) REFERENCES boxes (id), 
	CHECK (enabled IN (0, 1))
);

ALTER TABLE events ADD COLUMN deleted BOOLEAN NOT NULL CHECK (deleted IN (0, 1));
ALTER TABLE events ADD COLUMN deleted_timestamp DATETIME;
ALTER TABLE events ADD COLUMN deleted_user_id INTEGER FOREIGN KEY(deleted_user_id) REFERENCES users (id);

CREATE TABLE receipts (
	id INTEGER NOT NULL, 
	event_id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	receipt BLOB NOT NULL, 
	deleted BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(event_id) REFERENCES events (id), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	CHECK (deleted IN (0, 1))
);

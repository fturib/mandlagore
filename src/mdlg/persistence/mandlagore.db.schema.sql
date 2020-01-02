BEGIN TRANSACTION;
DROP TABLE IF EXISTS "config";
CREATE TABLE IF NOT EXISTS "config" (
	"version"	INTEGER
);
DROP INDEX IF EXISTS "pk_images";
DROP TABLE IF EXISTS "images";
CREATE TABLE IF NOT EXISTS "images" (
	"imageID"	TEXT,     -- imageID = correspond to a pageID which is DocumentID + "-" + NumPage
	"documentURL"	TEXT, -- download the image. May have different forma depending the server of images (Gallica, DRE, etc ...)
	"width"	INTEGER,      -- size in pixel of the image downloaded with 'documentURL'
	"height"	INTEGER
);
CREATE UNIQUE INDEX IF NOT EXISTS "pk_images" ON "images" (
	"imageID"  -- WARNING: if the same image is delivered by several servers, the program wil have to deal with picking the most trustable one.
);

DROP INDEX IF EXISTS "pk_classes";
DROP TABLE IF EXISTS "classes";
CREATE TABLE IF NOT EXISTS "classes" (
	"classID"	TEXT,
	"superclassID"	TEXT,
	"label" TEXT
);


CREATE UNIQUE INDEX IF NOT EXISTS "pk_classes" ON "classes" (
	"classID"	ASC
);
DROP INDEX IF EXISTS "pk_mandragore";
DROP TABLE IF EXISTS "mandragores";
CREATE TABLE IF NOT EXISTS "mandragores" (
	"mandragoreID"	INTEGER, -- pk of this table
	"description" TEXT
);

DROP INDEX IF EXISTS "pk_scenes";
DROP INDEX IF EXISTS "fk_scenes_mandragores";
DROP INDEX IF EXISTS "fk_scenes_images";
DROP TABLE IF EXISTS "scenes";
CREATE TABLE IF NOT EXISTS "scenes" (
	"mandragoreID"	INTEGER, -- pk of this table, fk om mandragores
	"imageID"	TEXT,        -- pk of this table, fk on images
	"x"	FLOAT,               -- x, y are part of pk - location and size of this scene relative to image. Values in pct. x, y middle of the zone
	"y"	FLOAT,
	"width"	FLOAT,
	"height"	FLOAT
);
CREATE UNIQUE INDEX IF NOT EXISTS "pk_scenes" ON "scenes" (
	"mandragoreID",
	"imageID",
	"x",
	"y"
);
CREATE INDEX IF NOT EXISTS "fk_scenes_mandragores" ON "mandragores" (
	"mandragoreID"	ASC
);
CREATE INDEX IF NOT EXISTS "fk_scenes_images" ON "scenes" (
	"imageID"	ASC
);

DROP INDEX IF EXISTS "pk_descriptors";
DROP INDEX IF EXISTS "fk_descriptors_mandragores";
DROP INDEX IF EXISTS "fk_descriptors_classes";
DROP TABLE IF EXISTS "descriptors";
CREATE TABLE IF NOT EXISTS "descriptors" (
	"mandragoreID"	INTEGER, -- fk to scene - part of pk.
	"classID" TEXT,           -- fk to class - part of pk.
	"x"	FLOAT,               -- location of the class relative to image. values in pct. x, y middle of the zone
	"y"	FLOAT,
	"width"	FLOAT,
	"height"	FLOAT
);
CREATE UNIQUE INDEX IF NOT EXISTS "pk_descriptors" ON "descriptors" (
	"mandragoreID",
	"classID"
);
CREATE INDEX IF NOT EXISTS "fk_descriptors_mandragores" ON "mandragores" (
	"mandragoreID"	ASC
);
CREATE INDEX IF NOT EXISTS "fk_descriptors_classes" ON "classes" (
	"classID"	ASC
);
INSERT INTO config VALUES (1);
COMMIT;

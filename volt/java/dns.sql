CREATE TABLE DNS (
   sender VARCHAR(32) NOT NULL,
   firstseen TIMESTAMP  DEFAULT CURRENT_TIMESTAMP NOT NULL,
   domain VARCHAR(256) NOT NULL,
   response VARCHAR(15),
   rrcode TINYINT,
   clusterid VARCHAR(15),
  PRIMARY KEY (domain, response, sender)
);
PARTITION TABLE dns ON COLUMN domain;

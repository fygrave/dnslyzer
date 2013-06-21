CREATE TABLE DNS (
   sender VARCHAR(32)
   firstseen TIMESTAMP,
   domain VARCHAR(256),
   response VARCHAR(15),
   rrcode BYTE,
   clusterid VARCHAR(15),
  PRIMARY KEY (DOMAIN, RESPONSE, sender)
);
PARTITION TABLE dns ON COLUMN domain;

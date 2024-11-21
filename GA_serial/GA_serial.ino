
#include <SoftwareSerial.h>
 
SoftwareSerial mySerial(2,3); 
char incomingByte = 0; // for incoming serial data
void setup()
{
    // Open serial communications and wait for port to open:
    Serial.begin(19200);
    mySerial.begin(19200);
}
 
void loop() 
{
if (mySerial.available() > 0) {
    if (mySerial.available())
    Serial.write(mySerial.read());
    if (Serial.available())
    mySerial.write(Serial.read());
  }
}

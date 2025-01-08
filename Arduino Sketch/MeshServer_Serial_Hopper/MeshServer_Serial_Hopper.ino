
#include <SPI.h>
#include <RH_RF69.h>
#include <RHMesh.h>
#include <RTCZero.h>

/************ Radio Setup ***************/

// Change to 433.0 or other frequency, must match RX's freq!
#define RF69_FREQ 433.0

// ID String so the host computer can identify the board
#define ID_STRING "!Turtle Dyne"

// who am i? (server address)
#define SERVER1_ADDRESS 1
#define RH_HAVE_SERIAL 1

#define RFM69_CS 8
#define RFM69_INT 3
#define RFM69_RST 4
#define LED 13

// Singleton instance of the radio driver
RH_RF69 driver(RFM69_CS, RFM69_INT);

// Class to manage message delivery and receipt, using the driver declared above
RHMesh manager(driver, SERVER1_ADDRESS);
 
void setup() 
{
  Serial.begin(19200);
  if (!manager.init())
    Serial.println("RF22 init failed");
  driver.setTxPower(20, true);
  driver.setModemConfig(driver.GFSK_Rb2Fd5);
}
 
uint8_t data[54]; //the max length to send is 54!! DON'T BELEIVE THE DOCUMENTATION. IT'S 54
uint8_t buf[RH_MESH_MAX_MESSAGE_LEN];
int i=0; 
char serial_buf;

void loop()
{
  uint8_t len = sizeof(buf);
  uint8_t from;
  if (manager.recvfromAck(buf, &len, &from))
  {
    // Serial.print("got request from : 0x");
    // Serial.print(from, HEX);
    // Serial.print(": ");
    //Serial.print("RSSI:");
    //Serial.print(driver.lastRssi());
    //Serial.print(" ");
    Serial.print((char*)buf);
  }
  // Check if serial commands have been sent and broadcast them
  if (Serial.available()) 
  {
    if (i<=53) 
    {
      digitalWrite(LED,HIGH);
      serial_buf = Serial.read();
      Serial.print(serial_buf);
      memcpy(&data[i],&serial_buf,sizeof(serial_buf));
      i++;
    }
  }
  if ((serial_buf == '\r') || (i>=53))  
  {
    // delay(100);// Don't send too fast
    digitalWrite(LED,LOW);
    int result = manager.sendtoWait(data, i+1, 255);
    i=0;
    memset(data, 0, sizeof(data));
    memset(&serial_buf,0,sizeof(serial_buf));
    
  }
}

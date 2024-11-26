
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
}
 
uint8_t data[] = "And hello back to you from server1";
// Dont put this on the stack:
uint8_t buf[RH_MESH_MAX_MESSAGE_LEN];
void loop()
{
  uint8_t len = sizeof(buf);
  uint8_t from;
  if (manager.recvfromAck(buf, &len, &from))
  {
    // Serial.print("got request from : 0x");
    // Serial.print(from, HEX);
    // Serial.print(": ");
    Serial.print((char*)buf);
 
    // Send a reply back to the originator client
    if (manager.sendtoWait(data, sizeof(data), from) != RH_ROUTER_ERROR_NONE)
      Serial.println("sendtoWait failed");
  }
}

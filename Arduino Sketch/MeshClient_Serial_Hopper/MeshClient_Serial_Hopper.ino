// rf69 demo tx rx.pde
// -*- mode: C++ -*-
// Example sketch showing how to create a simple addressed, reliable messaging client
// with the RH_RF69 class. RH_RF69 class does not provide for addressing or
// reliability, so you should only use RH_RF69  if you do not need the higher
// level messaging abilities.
// It is designed to work with the other example rf69_server.
// Demonstrates the use of AES encryption, setting the frequency and modem
// configuration

#include <RH_RF69.h>
#include <RHMesh.h>
#include <RTCZero.h>
#include <SPI.h>

/************ Radio Setup ***************/

// Change to 433.0 or other frequency, must match RX's freq!
#define RF69_FREQ 433.0

// Where to send packets to!
#define SERVER1_ADDRESS 1
// change addresses for each client board, any number :)
#define CLIENT_ADDRESS 2

#define RFM69_CS 8
#define RFM69_INT 3
#define RFM69_RST 4
#define LED 13


#define VBATPIN A7


// Singleton instance of the radio driver
RH_RF69 driver(RFM69_CS, RFM69_INT);

// Class to manage message delivery and receipt, using the driver declared above
RHMesh manager(driver, CLIENT_ADDRESS);
 
void setup() 
{
  Serial.begin(19200);
  if (!manager.init())
    Serial.println("init failed");
  driver.setTxPower(20, true);
  
}
 
uint8_t data[54]; //the max length to send is 54!! DON'T BELEIVE THE DOCUMENTATION. IT'S 54
// Dont put this on the stack:
uint8_t buf[RH_MESH_MAX_MESSAGE_LEN];
int i=0;
char serial_buf;
 
void loop()
{

  if (Serial.available()) 
  {
    if (i<=53) 
    {
      serial_buf = Serial.read();
      Serial.print(serial_buf);
      memcpy(&data[i],&serial_buf,sizeof(serial_buf));
      i++;
    }
  }
  if ((serial_buf == '\n') || (i>=53) || (serial_buf == '\r'))  
    {
      delay(50);// Don't send too fast
      Serial.println("Sending to manager_mesh_server");
      int result = manager.sendtoWait(data, i+1, SERVER1_ADDRESS);
      
      if (result == RH_ROUTER_ERROR_NONE) 
      {
        // It has been reliably delivered to the next node.
        // Now wait for a reply from the ultimate server
        uint8_t len = sizeof(buf);
        uint8_t from;    
        if (manager.recvfromAckTimeout(buf, &len, 3000, &from))
        {
          Serial.print("got reply from : 0x");
          Serial.print(from, HEX);
          Serial.print(": ");
          Serial.println((char*)buf);
        }
        else
          {
            Serial.println("No reply, is rf22_mesh_server1, rf22_mesh_server2 and rf22_mesh_server3 running?");
          }
      }
      else 
      {
        Serial.println("sendtoWait failed. Are the intermediate mesh servers running?");
      }
      i=0;
      memset(data, 0, sizeof(data));
      memset(&serial_buf,0,sizeof(serial_buf));
      
    }
}
  // // Send a message to a mesh_server
  // // A route to the destination will be automatically discovered.
  // if (manager.sendtoWait(data, sizeof(data), SERVER1_ADDRESS) == RH_ROUTER_ERROR_NONE)
  // {
  //   // It has been reliably delivered to the next node.
  //   // Now wait for a reply from the ultimate server
  //   uint8_t len = sizeof(buf);
  //   uint8_t from;    
  //   if (manager.recvfromAckTimeout(buf, &len, 3000, &from))
  //   {
  //     Serial.print("got reply from : 0x");
  //     Serial.print(from, HEX);
  //     Serial.print(": ");
  //     Serial.println((char*)buf);
  //   }
  //   else
  //   {
  //     Serial.println("No reply, is rf22_mesh_server1, rf22_mesh_server2 and rf22_mesh_server3 running?");
  //   }
  // }
  // else
  //    Serial.println("sendtoWait failed. Are the intermediate mesh servers running?");
  // }

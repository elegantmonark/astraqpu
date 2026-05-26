void setup() {
  Serial.begin(115200);
  Serial.println("{\"type\":\"HELLO\",\"proto\":\"astraqpu.serial.v0\",\"device\":\"arduino-placeholder\"}");
}

void loop() {
  if (Serial.available()) {
    String line = Serial.readStringUntil('\n');
    Serial.print("{\"type\":\"ACK\",\"echo_bytes\":");
    Serial.print(line.length());
    Serial.println("}");
  }
}


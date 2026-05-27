struct Instruction {
  int id;
  unsigned long t_ns;
  unsigned long duration_ns;
  unsigned long latency_ns;
  char op[16];
};

const int MAX_INSTRUCTIONS = 64;
Instruction instructions[MAX_INSTRUCTIONS];
int instruction_count = 0;
char job_id[32] = "job_001";

void setup() {
  Serial.begin(115200);
  while (!Serial) {
    ;
  }
  send_hello();
}

void loop() {
  if (Serial.available()) {
    String line = Serial.readStringUntil('\n');
    line.trim();
    if (line.length() == 0) {
      return;
    }
    handle_line(line);
  }
}

void handle_line(const String &line) {
  String type = json_string(line, "type");

  if (type == "HELLO") {
    send_hello();
    return;
  }

  if (type == "LOAD") {
    instruction_count = 0;
    copy_string(json_string(line, "job_id"), job_id, sizeof(job_id));
    ack("LOAD");
    return;
  }

  if (type == "INST") {
    if (instruction_count >= MAX_INSTRUCTIONS) {
      nack("instruction_buffer_full");
      return;
    }

    Instruction &instruction = instructions[instruction_count++];
    instruction.id = json_int(line, "id");
    instruction.t_ns = json_ulong(line, "t_ns");
    instruction.duration_ns = json_ulong(line, "duration_ns");
    instruction.latency_ns = json_ulong(line, "latency_ns");
    copy_string(json_string(line, "op"), instruction.op, sizeof(instruction.op));
    ack("INST");
    return;
  }

  if (type == "RUN") {
    ack("RUN");
    run_job();
    return;
  }

  nack("unknown_command");
}

void run_job() {
  unsigned long previous_ns = 0;

  for (int i = 0; i < instruction_count; i++) {
    Instruction &instruction = instructions[i];
    if (instruction.t_ns > previous_ns) {
      delay_ns(instruction.t_ns - previous_ns);
    }

    event("instruction_start", instruction, instruction.t_ns);
    delay_ns(instruction.duration_ns);
    event("instruction_end", instruction, instruction.t_ns + instruction.duration_ns);
    previous_ns = instruction.t_ns + instruction.duration_ns;

    if (instruction.latency_ns > 0) {
      delay_ns(instruction.latency_ns);
      event("latency_complete", instruction, instruction.t_ns + instruction.duration_ns + instruction.latency_ns);
      previous_ns += instruction.latency_ns;
    }
  }

  Serial.print("{\"type\":\"RESULT\",\"job_id\":\"");
  Serial.print(job_id);
  Serial.println("\",\"bits\":{}}");
  Serial.print("{\"type\":\"DONE\",\"job_id\":\"");
  Serial.print(job_id);
  Serial.println("\"}");
}

void delay_ns(unsigned long ns) {
  unsigned long us = ns / 1000;
  if (ns > 0 && us == 0) {
    us = 1;
  }
  if (us > 0) {
    delayMicroseconds(us);
  }
}

void send_hello() {
  Serial.println("{\"type\":\"HELLO\",\"proto\":\"astraqpu.serial.v0\",\"device\":\"arduino\",\"tick_ns\":1000}");
}

void ack(const char *command) {
  Serial.print("{\"type\":\"ACK\",\"job_id\":\"");
  Serial.print(job_id);
  Serial.print("\",\"command\":\"");
  Serial.print(command);
  Serial.println("\"}");
}

void nack(const char *reason) {
  Serial.print("{\"type\":\"NACK\",\"job_id\":\"");
  Serial.print(job_id);
  Serial.print("\",\"reason\":\"");
  Serial.print(reason);
  Serial.println("\"}");
}

void event(const char *event_name, const Instruction &instruction, unsigned long t_ns) {
  Serial.print("{\"type\":\"EVT\",\"job_id\":\"");
  Serial.print(job_id);
  Serial.print("\",\"event\":\"");
  Serial.print(event_name);
  Serial.print("\",\"id\":");
  Serial.print(instruction.id);
  Serial.print(",\"op\":\"");
  Serial.print(instruction.op);
  Serial.print("\",\"t_ns\":");
  Serial.print(t_ns);
  Serial.println("}");
}

String json_string(const String &line, const char *key) {
  String pattern = String("\"") + key + "\":\"";
  int start = line.indexOf(pattern);
  if (start < 0) {
    return "";
  }
  start += pattern.length();
  int end = line.indexOf("\"", start);
  if (end < 0) {
    return "";
  }
  return line.substring(start, end);
}

int json_int(const String &line, const char *key) {
  return (int)json_ulong(line, key);
}

unsigned long json_ulong(const String &line, const char *key) {
  String pattern = String("\"") + key + "\":";
  int start = line.indexOf(pattern);
  if (start < 0) {
    return 0;
  }
  start += pattern.length();
  int end = start;
  while (end < line.length() && isDigit(line[end])) {
    end++;
  }
  return line.substring(start, end).toInt();
}

void copy_string(const String &value, char *target, size_t target_size) {
  value.toCharArray(target, target_size);
  target[target_size - 1] = '\0';
}

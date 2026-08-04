import { describe, expect, it } from "vitest";

import { parseAttendanceCode } from "../lib/attendance";

describe("parseAttendanceCode", () => {
  it("extracts the code from the backend AttendPro QR URI", () => {
    expect(parseAttendanceCode("attendpro://mark?schedule_id=654321&code=123456")).toBe("123456");
  });

  it("accepts a raw six digit code", () => {
    expect(parseAttendanceCode(" 123456 ")).toBe("123456");
  });

  it("rejects missing, malformed, and unrelated six digit values", () => {
    expect(parseAttendanceCode("attendpro://mark?schedule_id=654321")).toBeNull();
    expect(parseAttendanceCode("attendpro://mark?code=12345")).toBeNull();
    expect(parseAttendanceCode("schedule 654321")).toBeNull();
  });
});

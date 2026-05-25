import { describe, it, expect } from "vitest";
import { middleware } from "./middleware";
import { NextRequest } from "next/server";

function createMockRequest(
  path: string,
  cookies: Record<string, string> = {},
): NextRequest {
  const url = new URL(path, "http://localhost:3000");
  const request = new NextRequest(url);
  for (const [name, value] of Object.entries(cookies)) {
    request.cookies.set(name, value);
  }
  return request;
}

describe("middleware", () => {
  describe("employee route protection", () => {
    it("redirects to /login when no access_token cookie on /employee routes", () => {
      const request = createMockRequest("/employee/dashboard");
      const response = middleware(request);

      expect(response.status).toBe(307);
      expect(response.headers.get("location")).toBe(
        "http://localhost:3000/login",
      );
    });

    it("redirects to /login when no access_token cookie on /employee/profile", () => {
      const request = createMockRequest("/employee/profile");
      const response = middleware(request);

      expect(response.status).toBe(307);
      expect(response.headers.get("location")).toBe(
        "http://localhost:3000/login",
      );
    });

    it("allows request through when access_token cookie exists on /employee routes", () => {
      const request = createMockRequest("/employee/dashboard", {
        access_token: "some-valid-token",
      });
      const response = middleware(request);

      expect(response.status).toBe(200);
      expect(response.headers.get("location")).toBeNull();
    });

    it("allows request through when access_token exists on /employee/attendance", () => {
      const request = createMockRequest("/employee/attendance", {
        access_token: "some-valid-token",
      });
      const response = middleware(request);

      expect(response.status).toBe(200);
      expect(response.headers.get("location")).toBeNull();
    });
  });

  describe("admin dashboard route protection", () => {
    it("redirects to /login when no access_token on admin routes", () => {
      const request = createMockRequest("/admin/users");
      const response = middleware(request);

      expect(response.status).toBe(307);
      expect(response.headers.get("location")).toBe(
        "http://localhost:3000/login",
      );
    });

    it("allows request through when access_token exists on admin routes", () => {
      const request = createMockRequest("/admin/users", {
        access_token: "some-valid-token",
      });
      const response = middleware(request);

      expect(response.status).toBe(200);
      expect(response.headers.get("location")).toBeNull();
    });
  });

  describe("general route protection", () => {
    it("redirects to /login when no access_token on unmatched routes", () => {
      const request = createMockRequest("/some-other-page");
      const response = middleware(request);

      expect(response.status).toBe(307);
      expect(response.headers.get("location")).toBe(
        "http://localhost:3000/login",
      );
    });

    it("allows request through when access_token exists on general routes", () => {
      const request = createMockRequest("/some-other-page", {
        access_token: "some-valid-token",
      });
      const response = middleware(request);

      expect(response.status).toBe(200);
      expect(response.headers.get("location")).toBeNull();
    });
  });
});

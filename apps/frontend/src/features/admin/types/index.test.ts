import { describe, expect, it } from "vitest";
import { hasRole, isStaff, ROLE_HIERARCHY } from "./index";

describe("role hierarchy", () => {
  it("admin is superset of all", () => {
    expect(hasRole("admin", "user")).toBe(true);
    expect(hasRole("admin", "moderator")).toBe(true);
    expect(hasRole("admin", "support")).toBe(true);
    expect(hasRole("admin", "admin")).toBe(true);
  });

  it("user has no staff privileges", () => {
    expect(hasRole("user", "user")).toBe(true);
    expect(hasRole("user", "moderator")).toBe(false);
  });

  it("support inherits moderator", () => {
    expect(hasRole("support", "moderator")).toBe(true);
    expect(hasRole("support", "admin")).toBe(false);
  });

  it("moderator does NOT get support powers (refunds, ban)", () => {
    expect(hasRole("moderator", "support")).toBe(false);
  });

  it("isStaff is true at moderator and above only", () => {
    expect(isStaff("user")).toBe(false);
    expect(isStaff("moderator")).toBe(true);
    expect(isStaff("support")).toBe(true);
    expect(isStaff("admin")).toBe(true);
  });

  it("rejects unknown roles (defence in depth)", () => {
    expect(hasRole("god-mode", "user")).toBe(false);
    expect(hasRole(null, "user")).toBe(false);
    expect(hasRole(undefined, "user")).toBe(false);
    expect(hasRole("", "user")).toBe(false);
  });

  it("hierarchy ordering is stable", () => {
    expect(ROLE_HIERARCHY).toEqual(["user", "moderator", "support", "admin"]);
  });
});

export type UserRole = "user" | "moderator" | "support" | "admin";

export const ROLE_HIERARCHY: UserRole[] = ["user", "moderator", "support", "admin"];

export function hasRole(role: string | undefined | null, required: UserRole): boolean {
  if (!role) return false;
  const userIdx = ROLE_HIERARCHY.indexOf(role as UserRole);
  const requiredIdx = ROLE_HIERARCHY.indexOf(required);
  return userIdx >= 0 && userIdx >= requiredIdx;
}

/** True when the user is staff (moderator+) — gates the /admin link in the sidebar. */
export const isStaff = (role: string | undefined | null) =>
  hasRole(role, "moderator");

export interface AdminTemplateRow {
  id: string;
  slug: string;
  title: string;
  author_user_id: string;
  author_email: string | null;
  author_name: string;
  status: string;
  is_featured: boolean;
  price_cents: number;
  fork_count: number;
  rating_avg: string | null;
  rating_count: number;
  created_at: string;
  published_at: string | null;
}

export interface AdminUserRow {
  id: string;
  email: string;
  full_name: string | null;
  role: UserRole;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
  last_login_at: string | null;
  // Stripe Connect onboarding state — surfaced so admins can see at a
  // glance whether an author can be paid for paid templates.
  stripe_account_id: string | null;
  stripe_charges_enabled: boolean;
  stripe_payouts_enabled: boolean;
}

export interface AdminPurchaseRow {
  id: string;
  buyer_user_id: string;
  buyer_email: string | null;
  template_id: string;
  template_title: string | null;
  price_paid_cents: number;
  currency: string;
  status: string;
  provider_transaction_id: string | null;
  purchased_at: string;
  refunded_at: string | null;
}

export interface AdminStats {
  total_users: number;
  active_users_30d: number;
  total_templates: number;
  published_templates: number;
  total_forks: number;
  total_purchases_paid: number;
  revenue_cents_30d: number;
  revenue_cents_all_time: number;
}

export interface AdminAction {
  id: string;
  actor_user_id: string | null;
  actor_email: string | null;
  action: string;
  target_type: string | null;
  target_id: string | null;
  details: Record<string, unknown>;
  created_at: string;
}

export interface TemplateModerationInput {
  is_featured?: boolean;
  status?: "draft" | "published" | "suspended" | "archived";
  reason?: string;
}

export interface UserBanInput {
  is_active: boolean;
  reason?: string;
}

export interface GrantRoleInput {
  role: UserRole;
}

export interface PayoutSuspendInput {
  enabled: boolean;
  reason?: string;
}

import { redirect } from "next/navigation";

// Landing for /system → executive overview.
export default function Page() {
  redirect("/system/dashboard");
}

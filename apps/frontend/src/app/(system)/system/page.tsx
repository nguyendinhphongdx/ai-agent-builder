import { redirect } from "next/navigation";

// Landing for /system → push to the first usable page.
export default function Page() {
  redirect("/system/organizations");
}

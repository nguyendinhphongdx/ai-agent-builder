import { redirect } from "next/navigation";

export const metadata = { title: "Settings" };

/** /settings has no content of its own — bounce to the first tab so deep
 *  links and the sidebar entry both land somewhere meaningful. */
export default function SettingsIndexPage() {
  redirect("/settings/profile");
}

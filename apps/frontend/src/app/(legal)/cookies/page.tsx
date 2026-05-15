import Link from "next/link";
import {
  LegalHeader,
  LegalSection,
  legalMetadata,
} from "../_components/LegalShell";

export const metadata = legalMetadata("Chính sách Cookie");

export default function CookiesPage() {
  return (
    <article>
      <LegalHeader
        title="Chính sách Cookie"
        subtitle="Cookie nào chúng tôi sử dụng, mục đích, và cách bạn kiểm soát chúng."
      />

      <LegalSection title="Cookie là gì?">
        <p>
          Cookie là tệp văn bản nhỏ trình duyệt lưu khi bạn truy cập một trang
          web. Chúng tôi sử dụng cookie để giữ phiên đăng nhập, chống tấn công
          CSRF, và cải thiện trải nghiệm.
        </p>
      </LegalSection>

      <LegalSection title="Phân loại cookie chúng tôi dùng">
        <table className="w-full border-collapse text-xs">
          <thead>
            <tr className="border-b border-border">
              <th className="py-2 text-left font-semibold">Tên</th>
              <th className="py-2 text-left font-semibold">Loại</th>
              <th className="py-2 text-left font-semibold">Mục đích</th>
              <th className="py-2 text-left font-semibold">TTL</th>
            </tr>
          </thead>
          <tbody className="text-foreground/80">
            <tr className="border-b border-border/50">
              <td className="py-2 font-mono">access_token</td>
              <td className="py-2">Cần thiết</td>
              <td className="py-2">JWT phiên đăng nhập</td>
              <td className="py-2">15 phút</td>
            </tr>
            <tr className="border-b border-border/50">
              <td className="py-2 font-mono">refresh_token</td>
              <td className="py-2">Cần thiết</td>
              <td className="py-2">Làm mới phiên (HttpOnly, scoped)</td>
              <td className="py-2">7-30 ngày</td>
            </tr>
            <tr className="border-b border-border/50">
              <td className="py-2 font-mono">csrftoken</td>
              <td className="py-2">Cần thiết</td>
              <td className="py-2">Chống tấn công CSRF</td>
              <td className="py-2">Phiên</td>
            </tr>
            <tr className="border-b border-border/50">
              <td className="py-2 font-mono">agentforge:cookie-consent</td>
              <td className="py-2">Tiện ích</td>
              <td className="py-2">Ghi nhớ lựa chọn cookie banner</td>
              <td className="py-2">365 ngày</td>
            </tr>
            <tr>
              <td className="py-2 font-mono">_stripe_*</td>
              <td className="py-2">Bên thứ ba</td>
              <td className="py-2">Stripe Checkout, payment processing</td>
              <td className="py-2">Theo Stripe</td>
            </tr>
          </tbody>
        </table>
      </LegalSection>

      <LegalSection title="Cookie cần thiết">
        <p>
          Các cookie này không thể tắt — chúng cần để dịch vụ hoạt động cơ bản
          (đăng nhập, bảo mật). Việc sử dụng dịch vụ đồng nghĩa với chấp nhận
          các cookie này.
        </p>
      </LegalSection>

      <LegalSection title="Cookie không thiết yếu (analytics/marketing)">
        <p>
          Hiện tại chúng tôi KHÔNG đặt cookie analytics/marketing tracking.
          Nếu sau này có thêm (Google Analytics, Plausible, v.v.) chúng tôi sẽ
          cập nhật bảng trên và yêu cầu sự đồng ý của Bạn trước khi đặt.
        </p>
      </LegalSection>

      <LegalSection title="Quản lý cookie">
        <p>
          Bạn có thể xoá cookie hoặc chặn chúng trong cài đặt trình duyệt. Lưu ý
          xoá <code className="rounded bg-muted/40 px-1.5 py-0.5 text-[11px]">access_token</code>{" "}
          và <code className="rounded bg-muted/40 px-1.5 py-0.5 text-[11px]">refresh_token</code>{" "}
          sẽ tự động đăng xuất khỏi tài khoản.
        </p>
        <p>
          Xem thêm tại{" "}
          <Link href="/privacy">Chính sách Bảo mật</Link>.
        </p>
      </LegalSection>
    </article>
  );
}

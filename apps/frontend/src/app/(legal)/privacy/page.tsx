import Link from "next/link";
import {
  LEGAL_ENTITY,
  LegalHeader,
  LegalSection,
  legalMetadata,
} from "../_components/LegalShell";

export const metadata = legalMetadata("Chính sách Bảo mật");

export default function PrivacyPage() {
  return (
    <article>
      <LegalHeader
        title="Chính sách Bảo mật"
        subtitle={`Chính sách này mô tả cách ${LEGAL_ENTITY.name} thu thập, sử dụng, và bảo vệ dữ liệu cá nhân của bạn khi sử dụng dịch vụ ${LEGAL_ENTITY.shortName}. Tuân thủ Nghị định 13/2023/NĐ-CP về Bảo vệ Dữ liệu Cá nhân.`}
      />

      <LegalSection title="1. Bên Kiểm soát Dữ liệu">
        <p>
          {LEGAL_ENTITY.name}, có trụ sở tại {LEGAL_ENTITY.address}, MST/ĐKKD{" "}
          {LEGAL_ENTITY.registrationNumber}, là Bên Kiểm soát Dữ liệu (Data
          Controller) cho mục đích của Chính sách này.
        </p>
        <p>
          Liên hệ về Dữ liệu Cá nhân:{" "}
          <a href={`mailto:${LEGAL_ENTITY.dpoEmail}`}>
            {LEGAL_ENTITY.dpoEmail}
          </a>
        </p>
      </LegalSection>

      <LegalSection title="2. Dữ liệu chúng tôi thu thập">
        <p>
          <strong>Dữ liệu Bạn cung cấp trực tiếp:</strong>
        </p>
        <ul className="ml-5 list-disc space-y-1">
          <li>
            Thông tin tài khoản: họ tên, email, mật khẩu (chỉ lưu hash bcrypt,
            không lưu plaintext), ảnh đại diện.
          </li>
          <li>
            Thông tin thanh toán: tên công ty/cá nhân, MST, địa chỉ thanh toán.
            Chúng tôi KHÔNG lưu số thẻ tín dụng — toàn bộ xử lý qua Stripe (PCI
            DSS Level 1).
          </li>
          <li>
            Nội dung Bạn tạo: prompt, agent config, knowledge base, workflow,
            tài liệu upload, tin nhắn chat.
          </li>
          <li>
            API keys của nhà cung cấp LLM bên ngoài: được mã hóa AES-256 (Fernet)
            trong DB; chỉ giải mã tại thời điểm gọi API.
          </li>
        </ul>
        <p>
          <strong>Dữ liệu thu thập tự động:</strong>
        </p>
        <ul className="ml-5 list-disc space-y-1">
          <li>
            Log sử dụng: timestamp request, IP, user-agent, endpoint, response
            code, response time.
          </li>
          <li>
            Telemetry sử dụng AI: số token đầu vào/ra, model được gọi, cost ước
            tính, latency. Cần để tính quota và bill chính xác.
          </li>
          <li>
            Cookie kỹ thuật: session/refresh token (HttpOnly, Secure), CSRF
            token. Xem{" "}
            <Link href="/cookies">Chính sách Cookie</Link> để biết chi tiết.
          </li>
        </ul>
        <p>
          <strong>Dữ liệu từ bên thứ ba (khi Bạn chọn liên kết):</strong> hồ sơ
          Google/Microsoft khi đăng nhập qua OAuth (chỉ email và họ tên hiển
          thị); tài khoản Stripe Connect khi đăng ký bán template trên Hub.
        </p>
      </LegalSection>

      <LegalSection title="3. Mục đích xử lý và cơ sở pháp lý">
        <p>
          Chúng tôi xử lý dữ liệu cá nhân của Bạn cho các mục đích sau, mỗi mục
          đích có cơ sở pháp lý tương ứng theo Nghị định 13/2023:
        </p>
        <ul className="ml-5 list-disc space-y-2">
          <li>
            <strong>Cung cấp dịch vụ</strong> (đăng nhập, lưu agent/KB, chạy
            workflow, gọi LLM) — <em>cơ sở: thực hiện hợp đồng</em>.
          </li>
          <li>
            <strong>Tính phí và xử lý thanh toán</strong> — <em>cơ sở: thực hiện
            hợp đồng và nghĩa vụ pháp lý (hóa đơn, thuế)</em>.
          </li>
          <li>
            <strong>Phát hiện gian lận, bảo mật, chống lạm dụng</strong> (rate
            limit, brute-force lockout, audit log) — <em>cơ sở: lợi ích hợp pháp
            của Chúng tôi và Người dùng khác</em>.
          </li>
          <li>
            <strong>Vận hành kỹ thuật và sửa lỗi</strong> (Sentry error
            tracking, log retention 90 ngày) — <em>cơ sở: lợi ích hợp pháp</em>.
          </li>
          <li>
            <strong>Gửi email transactional</strong> (xác nhận email, reset mật
            khẩu, hóa đơn) — <em>cơ sở: thực hiện hợp đồng</em>.
          </li>
          <li>
            <strong>Gửi email marketing / sản phẩm</strong> — <em>cơ sở: sự đồng
            ý của Bạn</em>; có thể rút lại bất kỳ lúc nào qua link unsubscribe.
          </li>
        </ul>
      </LegalSection>

      <LegalSection title="4. Chia sẻ dữ liệu với bên thứ ba">
        <p>
          Chúng tôi KHÔNG bán dữ liệu cá nhân. Chúng tôi chỉ chia sẻ trong các
          trường hợp sau:
        </p>
        <ul className="ml-5 list-disc space-y-1">
          <li>
            <strong>Nhà cung cấp LLM</strong> (OpenAI, Anthropic, Google AI):
            prompt và context Bạn gửi để generate response. Bạn có quyền cấu
            hình model trong agent settings; chọn model self-hosted (Ollama) sẽ
            không gửi data ra ngoài.
          </li>
          <li>
            <strong>Stripe</strong> (xử lý thanh toán, Connect payout): tên,
            email, địa chỉ thanh toán, lịch sử giao dịch. Stripe có chính sách
            bảo mật riêng tại stripe.com/privacy.
          </li>
          <li>
            <strong>Sentry</strong> (theo dõi lỗi): stack trace, request id,
            user id (nếu liên quan đến lỗi). KHÔNG bao gồm prompt/output LLM.
          </li>
          <li>
            <strong>Hạ tầng đám mây</strong>: nhà cung cấp hosting đặt máy chủ
            tại Việt Nam hoặc Singapore tuỳ deployment.
          </li>
          <li>
            <strong>Cơ quan có thẩm quyền</strong>: khi có yêu cầu hợp lệ theo
            quy định pháp luật Việt Nam.
          </li>
        </ul>
      </LegalSection>

      <LegalSection title="5. Chuyển dữ liệu ra nước ngoài">
        <p>
          Việc gọi LLM (OpenAI, Anthropic) có thể chuyển prompt và metadata sang
          máy chủ ở Mỹ hoặc EU. Việc lưu dữ liệu thanh toán trên Stripe diễn ra
          tại Mỹ. Chúng tôi đảm bảo các nhà cung cấp này tuân thủ tiêu chuẩn bảo
          mật quốc tế (SOC 2, ISO 27001).
        </p>
        <p>
          Người dùng tại Việt Nam có thể chọn chỉ dùng model self-hosted (Ollama)
          để giữ data hoàn toàn trong lãnh thổ Việt Nam.
        </p>
      </LegalSection>

      <LegalSection title="6. Thời gian lưu trữ">
        <ul className="ml-5 list-disc space-y-1">
          <li>Tài khoản đang hoạt động: lưu vô thời hạn cho đến khi xóa.</li>
          <li>
            Sau khi yêu cầu xóa tài khoản: xóa khỏi hệ thống sản phẩm trong 30
            ngày; backup được giữ tối đa 90 ngày để khôi phục thảm họa rồi xóa.
          </li>
          <li>Audit log: 90 ngày (Free), 365 ngày (Enterprise).</li>
          <li>
            Dữ liệu thanh toán: lưu 10 năm theo quy định kế toán Việt Nam (Luật
            Kế toán 2015).
          </li>
        </ul>
      </LegalSection>

      <LegalSection title="7. Quyền của Bạn">
        <p>
          Theo Nghị định 13/2023/NĐ-CP, Bạn có các quyền sau đối với dữ liệu cá
          nhân của mình:
        </p>
        <ul className="ml-5 list-disc space-y-1">
          <li>
            <strong>Quyền truy cập</strong> — yêu cầu bản sao dữ liệu chúng tôi
            đang lưu về Bạn (export JSON tại trang Cài đặt → Tài khoản).
          </li>
          <li>
            <strong>Quyền chỉnh sửa</strong> — sửa thông tin sai/lỗi thời tại
            Cài đặt Hồ sơ.
          </li>
          <li>
            <strong>Quyền xóa</strong> — yêu cầu xóa tài khoản và toàn bộ dữ
            liệu liên quan tại Cài đặt → Tài khoản → Xóa tài khoản.
          </li>
          <li>
            <strong>Quyền hạn chế / phản đối xử lý</strong> — yêu cầu Chúng tôi
            ngừng xử lý cho mục đích cụ thể (vd marketing).
          </li>
          <li>
            <strong>Quyền rút lại sự đồng ý</strong> — bất kỳ lúc nào, không
            ảnh hưởng tính hợp pháp xử lý trước đó.
          </li>
          <li>
            <strong>Quyền khiếu nại</strong> — gửi tới Cơ quan Bảo vệ Dữ liệu Cá
            nhân (Cục An toàn Thông tin — Bộ Thông tin & Truyền thông).
          </li>
        </ul>
        <p>
          Để thực hiện các quyền trên: gửi email tới{" "}
          <a href={`mailto:${LEGAL_ENTITY.dpoEmail}`}>
            {LEGAL_ENTITY.dpoEmail}
          </a>
          . Chúng tôi sẽ phản hồi trong 30 ngày làm việc.
        </p>
      </LegalSection>

      <LegalSection title="8. Biện pháp bảo mật">
        <ul className="ml-5 list-disc space-y-1">
          <li>Mật khẩu lưu dạng bcrypt; không bao giờ lưu plaintext.</li>
          <li>API keys mã hóa AES-256 (Fernet) trong DB.</li>
          <li>HTTPS bắt buộc cho mọi traffic; HSTS preload ready.</li>
          <li>Hỗ trợ MFA (TOTP) cho mọi tier.</li>
          <li>Per-account login lockout chống brute-force.</li>
          <li>
            Cookie session HttpOnly + Secure + SameSite=Lax; refresh token cookie
            phạm vi chỉ tới endpoint refresh.
          </li>
          <li>Phân lớp permission theo workspace/organization role.</li>
          <li>SSO/OIDC + SCIM cho khách hàng doanh nghiệp.</li>
          <li>Audit log mọi hành động nhạy cảm.</li>
        </ul>
      </LegalSection>

      <LegalSection title="9. Trẻ em">
        <p>
          Dịch vụ không dành cho người dưới 16 tuổi. Nếu phát hiện đã thu thập
          dữ liệu của người dưới 16 tuổi, Chúng tôi sẽ xóa ngay lập tức.
        </p>
      </LegalSection>

      <LegalSection title="10. Thay đổi Chính sách">
        <p>
          Chúng tôi có thể cập nhật Chính sách này. Thay đổi trọng yếu được
          thông báo qua email và in-app banner ít nhất 30 ngày trước khi có
          hiệu lực.
        </p>
      </LegalSection>

      <LegalSection title="11. Liên hệ">
        <p>
          Mọi yêu cầu liên quan đến dữ liệu cá nhân, vui lòng liên hệ:
        </p>
        <ul className="ml-5 list-disc">
          <li>
            Email DPO:{" "}
            <a href={`mailto:${LEGAL_ENTITY.dpoEmail}`}>
              {LEGAL_ENTITY.dpoEmail}
            </a>
          </li>
          <li>
            Email chung:{" "}
            <a href={`mailto:${LEGAL_ENTITY.contactEmail}`}>
              {LEGAL_ENTITY.contactEmail}
            </a>
          </li>
          <li>Địa chỉ: {LEGAL_ENTITY.address}</li>
        </ul>
      </LegalSection>
    </article>
  );
}

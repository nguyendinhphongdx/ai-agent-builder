import Link from "next/link";
import {
  LEGAL_ENTITY,
  LegalHeader,
  LegalSection,
  legalMetadata,
} from "../_components/LegalShell";

export const metadata = legalMetadata("Điều khoản dịch vụ");

export default function TermsPage() {
  return (
    <article>
      <LegalHeader
        title="Điều khoản dịch vụ"
        subtitle={`Điều khoản này điều chỉnh việc bạn sử dụng dịch vụ ${LEGAL_ENTITY.shortName} do ${LEGAL_ENTITY.name} cung cấp. Vui lòng đọc kỹ trước khi đăng ký tài khoản.`}
      />

      <LegalSection title="1. Định nghĩa">
        <p>
          <strong>"Dịch vụ"</strong> nghĩa là nền tảng {LEGAL_ENTITY.shortName} — bao
          gồm trang web, API, công cụ xây dựng AI agent, marketplace, và mọi tính
          năng đi kèm — vận hành bởi {LEGAL_ENTITY.name} (sau đây gọi là{" "}
          <strong>"Chúng tôi"</strong>).
        </p>
        <p>
          <strong>"Bạn"</strong> nghĩa là cá nhân hoặc tổ chức đăng ký, truy cập,
          hoặc sử dụng Dịch vụ.
        </p>
        <p>
          <strong>"Nội dung của Bạn"</strong> nghĩa là dữ liệu, prompt, tài liệu tri
          thức, agent, workflow, và mọi thông tin Bạn nhập vào Dịch vụ.
        </p>
      </LegalSection>

      <LegalSection title="2. Đăng ký tài khoản">
        <p>
          Bạn phải đủ 16 tuổi (hoặc tuổi được phép tham gia hợp đồng tại nơi cư
          trú) để mở tài khoản. Bạn chịu trách nhiệm cho tính chính xác của thông
          tin đăng ký và bảo mật mật khẩu/khóa API của mình. Mọi hoạt động phát
          sinh dưới tài khoản của Bạn được coi là do Bạn thực hiện.
        </p>
      </LegalSection>

      <LegalSection title="3. Sử dụng được phép">
        <p>Khi sử dụng Dịch vụ, Bạn cam kết KHÔNG:</p>
        <ul className="ml-5 list-disc space-y-1">
          <li>Vi phạm pháp luật Việt Nam hoặc pháp luật quốc tế có liên quan.</li>
          <li>
            Tạo hoặc phân phối nội dung khiêu dâm, kích động bạo lực, lừa đảo,
            phá hoại, hoặc xâm phạm quyền riêng tư người khác.
          </li>
          <li>
            Tấn công, dò quét, hoặc cố ý làm gián đoạn Dịch vụ (DDoS, scraping
            có hệ thống, brute-force, v.v.).
          </li>
          <li>
            Sử dụng Dịch vụ để vi phạm bản quyền, nhãn hiệu, bí mật kinh doanh
            của bên thứ ba.
          </li>
          <li>
            Bán lại quyền truy cập Dịch vụ (ngoại trừ template/agent trên
            marketplace chính thức) hoặc đăng ký tài khoản dưới danh tính giả.
          </li>
        </ul>
        <p>
          Chúng tôi có quyền đình chỉ hoặc chấm dứt tài khoản vi phạm sau khi đã
          thông báo, hoặc ngay lập tức trong trường hợp khẩn cấp.
        </p>
      </LegalSection>

      <LegalSection title="4. Quyền sở hữu trí tuệ">
        <p>
          <strong>Nội dung của Bạn</strong> thuộc sở hữu của Bạn. Bằng việc tải
          lên hoặc tạo Nội dung trong Dịch vụ, Bạn cấp cho Chúng tôi quyền sử
          dụng hạn chế — không độc quyền, có thể thu hồi, không trả phí — để xử
          lý, lưu trữ, hiển thị Nội dung đó nhằm vận hành Dịch vụ cho chính Bạn.
        </p>
        <p>
          Mã nguồn nền tảng {LEGAL_ENTITY.shortName} là mã nguồn mở giấy phép
          MIT (xem repository chính thức). Logo, thương hiệu, và bộ nhận diện
          {" "}{LEGAL_ENTITY.shortName} thuộc sở hữu của {LEGAL_ENTITY.name}.
        </p>
      </LegalSection>

      <LegalSection title="5. Phí dịch vụ và thanh toán">
        <p>
          Một số tính năng yêu cầu thanh toán theo gói (Starter, Pro, Enterprise)
          hoặc theo lượng sử dụng (token, KB queries). Mức giá và quota chi tiết
          công bố trên trang định giá. Phí được tính bằng VND hoặc USD theo phương
          thức thanh toán bạn chọn (Stripe, MoMo).
        </p>
        <p>
          Gói Subscription tự động gia hạn cuối mỗi chu kỳ trừ khi Bạn hủy
          trước ngày gia hạn. Lệnh hủy có hiệu lực từ cuối chu kỳ hiện tại; Chúng
          tôi không hoàn tiền cho phần đã thanh toán của chu kỳ đó (trừ trường
          hợp Pháp luật yêu cầu hoặc Chúng tôi tự nguyện).
        </p>
        <p>
          Nếu thanh toán thất bại, Bạn có 7 ngày để cập nhật phương thức thanh
          toán trước khi tài khoản bị giới hạn về tier miễn phí.
        </p>
      </LegalSection>

      <LegalSection title="6. Marketplace (Hub)">
        <p>
          Tác giả có thể đăng template/agent lên Hub để bán. Chúng tôi thu phí
          nền tảng 15% trên mỗi giao dịch thành công (chưa bao gồm phí xử lý
          thanh toán của Stripe). Tác giả chịu trách nhiệm về tính hợp pháp,
          chất lượng, và bản quyền của Nội dung họ đăng tải.
        </p>
        <p>
          Người mua được cấp quyền sử dụng không giới hạn template đã mua trong
          tài khoản của mình; KHÔNG được bán lại nguyên bản hoặc bản dẫn xuất
          không đáng kể.
        </p>
      </LegalSection>

      <LegalSection title="7. Bảo mật và dữ liệu cá nhân">
        <p>
          Cách Chúng tôi thu thập và xử lý dữ liệu cá nhân được quy định chi tiết
          trong{" "}
          <Link href="/privacy">Chính sách Bảo mật</Link>. Bằng việc sử dụng
          Dịch vụ, Bạn đồng ý với việc xử lý dữ liệu theo chính sách đó.
        </p>
      </LegalSection>

      <LegalSection title="8. Giới hạn trách nhiệm">
        <p>
          Dịch vụ được cung cấp "nguyên trạng" (as-is). Trong giới hạn pháp luật
          cho phép, Chúng tôi không chịu trách nhiệm cho:
        </p>
        <ul className="ml-5 list-disc space-y-1">
          <li>
            Output của các mô hình AI (LLM) — output có thể sai, thiên lệch, hoặc
            không phù hợp; Bạn chịu trách nhiệm thẩm định trước khi dùng cho việc
            quan trọng.
          </li>
          <li>
            Mất dữ liệu do lỗi của bên thứ ba (nhà cung cấp LLM, payment, hosting).
          </li>
          <li>
            Thiệt hại gián tiếp, mất lợi nhuận, hoặc thiệt hại do gián đoạn dịch
            vụ trong giới hạn pháp luật cho phép.
          </li>
        </ul>
        <p>
          Tổng trách nhiệm tài chính của Chúng tôi với Bạn trong bất kỳ vụ việc
          nào không vượt quá tổng phí Bạn đã trả cho Chúng tôi trong 12 tháng
          trước đó.
        </p>
      </LegalSection>

      <LegalSection title="9. Chấm dứt">
        <p>
          Bạn có thể xóa tài khoản bất kỳ lúc nào tại trang Cài đặt. Khi xóa, dữ
          liệu của Bạn sẽ bị xóa khỏi hệ thống sản phẩm trong vòng 30 ngày (chi
          tiết tại Chính sách Bảo mật). Chúng tôi có thể chấm dứt tài khoản
          vi phạm Điều khoản này.
        </p>
      </LegalSection>

      <LegalSection title="10. Luật áp dụng và giải quyết tranh chấp">
        <p>
          Điều khoản này được điều chỉnh bởi pháp luật Việt Nam. Mọi tranh chấp
          phát sinh sẽ được ưu tiên giải quyết qua thương lượng. Nếu không
          thành, tranh chấp sẽ được đưa ra Tòa án có thẩm quyền tại nơi
          {LEGAL_ENTITY.name} đặt trụ sở.
        </p>
      </LegalSection>

      <LegalSection title="11. Thay đổi Điều khoản">
        <p>
          Chúng tôi có thể cập nhật Điều khoản này theo thời gian. Thay đổi
          trọng yếu sẽ được thông báo qua email và in-app banner ít nhất 30 ngày
          trước khi có hiệu lực. Việc Bạn tiếp tục sử dụng Dịch vụ sau ngày hiệu
          lực được coi là đồng ý với Điều khoản mới.
        </p>
      </LegalSection>

      <LegalSection title="12. Liên hệ">
        <p>
          Câu hỏi về Điều khoản? Liên hệ chúng tôi tại{" "}
          <a href={`mailto:${LEGAL_ENTITY.contactEmail}`}>
            {LEGAL_ENTITY.contactEmail}
          </a>
          .
        </p>
        <p className="text-xs text-muted-foreground">
          {LEGAL_ENTITY.name} — {LEGAL_ENTITY.address} — MST/ĐKKD:{" "}
          {LEGAL_ENTITY.registrationNumber}
        </p>
      </LegalSection>
    </article>
  );
}

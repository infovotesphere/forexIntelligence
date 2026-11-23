import { Page } from "@/components/Page";
export const instant = false;

export default function Orders() {
  return <Page title="Orders" description="Pending and completed order activity" active="/orders"><div className="card empty">No order activity</div></Page>;
}

import { Page } from "@/components/Page";
import { OrderActivity } from "@/components/OrderActivity";

export const instant = false;

export default function Orders() {
  return (
    <Page title="Order activity" description="Practice with virtual funds or monitor read-only MT5 activity" active="/orders">
      <OrderActivity />
    </Page>
  );
}

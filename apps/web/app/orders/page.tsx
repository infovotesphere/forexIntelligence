import { Page } from "@/components/Page";
import { OrderActivity } from "@/components/OrderActivity";

export const instant = false;

export default function Orders() {
  return (
    <Page title="Order activity" description="Read-only open and completed broker activity" active="/orders">
      <OrderActivity />
    </Page>
  );
}

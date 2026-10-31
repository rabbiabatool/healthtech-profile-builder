import NoShowPredictor from "../../components/predictions/NoShowPredictor";

export const metadata = { title: "No-show estimate (educational)" };

export default function MemberPredictionsPage() {
  return <NoShowPredictor mode="member" />;
}
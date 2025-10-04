import { useParams } from "react-router-dom";

export default function Detail() {
  const { id } = useParams<{ id: string }>();

  return (
    <div>
      <h1>Chi tiết cho ID: {id}</h1>
    </div>
  );
}

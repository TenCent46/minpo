"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";

export default function ArticlePage() {
  const params = useParams();
  const article_num = params.article_num as string;
  const [article, setArticle] = useState<any>(null);

  useEffect(() => {
    fetch(`http://localhost:8000/laws/civilcode/${article_num}`)
      .then((res) => res.json())
      .then((json) => setArticle(json))
      .catch((err) => console.error(err));
  }, [article_num]);

  return (
    <div>
      <h1>民法 第{article_num}条</h1>
      {article ? (
        <pre>{JSON.stringify(article, null, 2)}</pre>
      ) : (
        "Loading..."
      )}
    </div>
  );
}
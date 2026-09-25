import Explorer from "../../components/explorer";
export default async function Page({
  params,
  searchParams,
}: {
  params: Promise<{ path?: string[] }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const { path = [] } = await params;
  const filters = await searchParams;
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(filters))
    if (typeof value === "string" && value) query.set(key, value);
  return (
    <Explorer
      key={path.join("/") + query.toString()}
      path={path}
      query={query.toString()}
    />
  );
}

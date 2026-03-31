import { readFileSync } from "node:fs";
import path from "node:path";

type RawBritainCity = {
  name: string;
  position: {
    x: number;
    y: number;
  };
};

type RawBritainEdge = {
  city_a: string;
  city_b: string;
  distance_ticks: number;
  traversal_mode?: "land" | "sea";
};

type RawBritainMap = {
  cities: Record<string, RawBritainCity>;
  edges: RawBritainEdge[];
};

export type BritainMapCity = {
  id: string;
  name: string;
  x: number;
  y: number;
};

export type BritainMapEdge = {
  id: string;
  cityA: string;
  cityB: string;
  distanceTicks: number;
  traversalMode: "land" | "sea";
};

export type BritainMapLayout = {
  cities: BritainMapCity[];
  edges: BritainMapEdge[];
  width: number;
  height: number;
  viewBox: string;
};

let cachedLayout: BritainMapLayout | null = null;

export function loadBritainMapLayout(): BritainMapLayout {
  if (cachedLayout !== null) {
    return cachedLayout;
  }

  const mapPath = path.join(process.cwd(), "..", "server", "data", "map_uk_1900.json");
  const rawMap = JSON.parse(readFileSync(mapPath, "utf8")) as RawBritainMap;
  const coordinatePadding = 48;
  const orderedCityIds = Object.keys(rawMap.cities).sort((left, right) =>
    rawMap.cities[left].name.localeCompare(rawMap.cities[right].name)
  );

  const cities = orderedCityIds.map((cityId) => ({
    id: cityId,
    name: rawMap.cities[cityId].name,
    x: rawMap.cities[cityId].position.x,
    y: rawMap.cities[cityId].position.y
  }));
  const edges = rawMap.edges
    .map((edge) => ({
      id: `${edge.city_a}-${edge.city_b}`,
      cityA: edge.city_a,
      cityB: edge.city_b,
      distanceTicks: edge.distance_ticks,
      traversalMode: edge.traversal_mode ?? "land"
    }))
    .sort((left, right) => left.id.localeCompare(right.id));
  const maxX = cities.reduce((currentMax, city) => Math.max(currentMax, city.x), 0);
  const maxY = cities.reduce((currentMax, city) => Math.max(currentMax, city.y), 0);
  const width = maxX + coordinatePadding * 2;
  const height = maxY + coordinatePadding * 2;

  cachedLayout = {
    cities,
    edges,
    width,
    height,
    viewBox: `0 0 ${width} ${height}`
  };

  return cachedLayout;
}

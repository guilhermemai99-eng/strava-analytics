export type PublicUser = {
  id: string;
  name: string;
  username: string;
  bio: string | null;
  city: string | null;
  avatarUrl: string | null;
};

export type FeedPost = {
  id: string;
  caption: string | null;
  imageUrl: string | null;
  distanceKm: number;
  durationSeconds: number;
  occurredAt: string;
  city: string | null;
  isPr: boolean;
  visibility: "public" | "followers" | "private";
  source: "manual" | "strava";
  hiddenAt: string | null;
  likeCount: number;
  commentCount: number;
  likedByMe: boolean;
  isMine: boolean;
  author: PublicUser;
};

export type PostComment = {
  id: string;
  body: string;
  createdAt: string;
  author: PublicUser;
};

import { PostSource, PostVisibility, type Post, type User } from "@prisma/client";
import { z } from "zod";
import { prisma } from "@/lib/db";
import { toPublicUser } from "@/lib/services/users";
import type { FeedPost, PostComment } from "@/lib/types";

export const createPostSchema = z.object({
  caption: z.string().trim().max(500).optional().nullable(),
  distanceKm: z.number().positive("Distance must be greater than 0"),
  durationSeconds: z.number().int().positive("Duration is required"),
  occurredAt: z.coerce.date(),
  city: z.string().trim().max(80).optional().nullable(),
  isPr: z.boolean().optional(),
  visibility: z.nativeEnum(PostVisibility).optional(),
  imageUrl: z.string().optional().nullable(),
});

export const updatePostSchema = z.object({
  caption: z.string().trim().max(500).optional().nullable(),
  visibility: z.nativeEnum(PostVisibility).optional(),
  hidden: z.boolean().optional(),
  isPr: z.boolean().optional(),
});

type PostWithRelations = Post & {
  author: Pick<User, "id" | "name" | "username" | "bio" | "city" | "avatarUrl">;
  _count: { likes: number; comments: number };
  likes?: { userId: string }[];
};

export function serializePost(
  post: PostWithRelations,
  viewerId: string | null,
): FeedPost {
  return {
    id: post.id,
    caption: post.caption,
    imageUrl: post.imageUrl,
    distanceKm: post.distanceKm,
    durationSeconds: post.durationSeconds,
    occurredAt: post.occurredAt.toISOString(),
    city: post.city,
    isPr: post.isPr,
    visibility: post.visibility,
    source: post.source,
    hiddenAt: post.hiddenAt ? post.hiddenAt.toISOString() : null,
    likeCount: post._count.likes,
    commentCount: post._count.comments,
    likedByMe: Boolean(post.likes?.some((like) => like.userId === viewerId)),
    isMine: post.authorId === viewerId,
    author: toPublicUser(post.author),
  };
}

const postInclude = (viewerId: string | null) => ({
  author: {
    select: {
      id: true,
      name: true,
      username: true,
      bio: true,
      city: true,
      avatarUrl: true,
    },
  },
  _count: { select: { likes: true, comments: true } },
  likes: viewerId
    ? { where: { userId: viewerId }, select: { userId: true } }
    : false,
});

export async function getFeed(viewerId: string) {
  const follows = await prisma.follow.findMany({
    where: { followerId: viewerId },
    select: { followingId: true },
  });
  const authorIds = [viewerId, ...follows.map((row) => row.followingId)];

  const posts = await prisma.post.findMany({
    where: {
      authorId: { in: authorIds },
      hiddenAt: null,
      OR: [
        { authorId: viewerId },
        { visibility: PostVisibility.public },
        {
          visibility: PostVisibility.followers,
          author: { followers: { some: { followerId: viewerId } } },
        },
      ],
    },
    include: postInclude(viewerId),
    orderBy: { createdAt: "desc" },
    take: 50,
  });

  return posts.map((post) => serializePost(post, viewerId));
}

export async function getPost(postId: string, viewerId: string | null) {
  const post = await prisma.post.findUnique({
    where: { id: postId },
    include: postInclude(viewerId),
  });
  if (!post) throw new Error("Post not found");
  if (!canViewPost(post, viewerId)) throw new Error("Post not found");
  return serializePost(post, viewerId);
}

function canViewPost(
  post: { authorId: string; visibility: PostVisibility; hiddenAt: Date | null },
  viewerId: string | null,
) {
  if (post.authorId === viewerId) return true;
  if (post.hiddenAt) return false;
  if (post.visibility === PostVisibility.public) return true;
  if (!viewerId) return false;
  if (post.visibility === PostVisibility.private) return false;
  return true;
}

export async function createPost(
  authorId: string,
  input: z.infer<typeof createPostSchema>,
) {
  const data = createPostSchema.parse(input);
  const post = await prisma.post.create({
    data: {
      authorId,
      caption: data.caption ?? null,
      distanceKm: data.distanceKm,
      durationSeconds: data.durationSeconds,
      occurredAt: data.occurredAt,
      city: data.city ?? null,
      isPr: data.isPr ?? false,
      visibility: data.visibility ?? PostVisibility.public,
      imageUrl: data.imageUrl ?? null,
      source: PostSource.manual,
    },
    include: postInclude(authorId),
  });
  return serializePost(post, authorId);
}

export async function updatePost(
  postId: string,
  authorId: string,
  input: z.infer<typeof updatePostSchema>,
) {
  const existing = await prisma.post.findUnique({ where: { id: postId } });
  if (!existing || existing.authorId !== authorId) {
    throw new Error("Post not found");
  }
  const data = updatePostSchema.parse(input);
  const post = await prisma.post.update({
    where: { id: postId },
    data: {
      caption: data.caption,
      visibility: data.visibility,
      isPr: data.isPr,
      hiddenAt:
        data.hidden === undefined
          ? undefined
          : data.hidden
            ? new Date()
            : null,
    },
    include: postInclude(authorId),
  });
  return serializePost(post, authorId);
}

export async function deletePost(postId: string, authorId: string) {
  const existing = await prisma.post.findUnique({ where: { id: postId } });
  if (!existing || existing.authorId !== authorId) {
    throw new Error("Post not found");
  }
  await prisma.post.delete({ where: { id: postId } });
  return { ok: true };
}

export async function toggleLike(postId: string, userId: string) {
  const post = await prisma.post.findUnique({ where: { id: postId } });
  if (!post) throw new Error("Post not found");

  const existing = await prisma.postLike.findUnique({
    where: { postId_userId: { postId, userId } },
  });
  if (existing) {
    await prisma.postLike.delete({
      where: { postId_userId: { postId, userId } },
    });
    return { liked: false };
  }
  await prisma.postLike.create({ data: { postId, userId } });
  return { liked: true };
}

export async function listComments(postId: string): Promise<PostComment[]> {
  const comments = await prisma.comment.findMany({
    where: { postId },
    include: {
      author: {
        select: {
          id: true,
          name: true,
          username: true,
          bio: true,
          city: true,
          avatarUrl: true,
        },
      },
    },
    orderBy: { createdAt: "asc" },
  });
  return comments.map((comment) => ({
    id: comment.id,
    body: comment.body,
    createdAt: comment.createdAt.toISOString(),
    author: toPublicUser(comment.author),
  }));
}

export async function addComment(postId: string, authorId: string, body: string) {
  const text = body.trim();
  if (!text) throw new Error("Comment cannot be empty");
  if (text.length > 280) throw new Error("Comment is too long");
  const post = await prisma.post.findUnique({ where: { id: postId } });
  if (!post) throw new Error("Post not found");
  const comment = await prisma.comment.create({
    data: { postId, authorId, body: text },
    include: {
      author: {
        select: {
          id: true,
          name: true,
          username: true,
          bio: true,
          city: true,
          avatarUrl: true,
        },
      },
    },
  });
  return {
    id: comment.id,
    body: comment.body,
    createdAt: comment.createdAt.toISOString(),
    author: toPublicUser(comment.author),
  } satisfies PostComment;
}

export async function getPostsByUsername(
  username: string,
  viewerId: string | null,
) {
  const user = await prisma.user.findUnique({
    where: { username: username.toLowerCase() },
  });
  if (!user) return [];

  const isOwner = viewerId === user.id;
  const posts = await prisma.post.findMany({
    where: isOwner
      ? { authorId: user.id }
      : {
          authorId: user.id,
          hiddenAt: null,
          OR: [
            { visibility: PostVisibility.public },
            ...(viewerId
              ? [
                  {
                    visibility: PostVisibility.followers,
                    author: { followers: { some: { followerId: viewerId } } },
                  },
                ]
              : []),
          ],
        },
    include: postInclude(viewerId),
    orderBy: { createdAt: "desc" },
  });

  return posts.map((post) => serializePost(post, viewerId));
}

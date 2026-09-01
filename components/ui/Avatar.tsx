import styles from "./Avatar.module.css";

type Props = {
  name: string;
  src?: string | null;
  size?: "sm" | "md" | "lg";
};

export function Avatar({ name, src, size = "md" }: Props) {
  const initial = name.trim().charAt(0).toUpperCase() || "P";
  return (
    <span className={`${styles.avatar} ${styles[size]}`}>
      {src ? (
        // User-uploaded avatars are local files; a plain img keeps this simple.
        // eslint-disable-next-line @next/next/no-img-element
        <img src={src} alt="" className={styles.image} />
      ) : (
        initial
      )}
    </span>
  );
}

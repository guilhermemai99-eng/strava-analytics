import Link from "next/link";
import styles from "./Button.module.css";

type Variant = "primary" | "ghost" | "inverse";

type Props = {
  children: React.ReactNode;
  variant?: Variant;
  href?: string;
  type?: "button" | "submit";
  onClick?: () => void;
  disabled?: boolean;
  block?: boolean;
  className?: string;
};

export function Button({
  children,
  variant = "primary",
  href,
  type = "button",
  onClick,
  disabled,
  block,
  className,
}: Props) {
  const classNames = [
    styles.button,
    styles[variant],
    block ? styles.block : "",
    className ?? "",
  ]
    .filter(Boolean)
    .join(" ");

  if (href) {
    return (
      <Link href={href} className={classNames}>
        {children}
      </Link>
    );
  }

  return (
    <button
      type={type}
      className={classNames}
      onClick={onClick}
      disabled={disabled}
    >
      {children}
    </button>
  );
}

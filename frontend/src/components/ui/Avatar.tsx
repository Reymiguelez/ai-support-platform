import { HTMLAttributes, forwardRef } from 'react';
import { cn } from '@/utils/helpers';
import { getInitials } from '@/utils/helpers';

interface AvatarProps extends HTMLAttributes<HTMLDivElement> {
  src?: string | null;
  alt?: string;
  name?: string;
  size?: 'sm' | 'md' | 'lg' | 'xl';
}

export const Avatar = forwardRef<HTMLDivElement, AvatarProps>(
  ({ className, src, alt, name, size = 'md', ...props }, ref) => {
    const sizeClasses = {
      sm: 'h-8 w-8 text-xs',
      md: 'h-10 w-10 text-sm',
      lg: 'h-12 w-12 text-base',
      xl: 'h-16 w-16 text-lg',
    };

    return (
      <div
        ref={ref}
        className={cn(
          'relative inline-flex shrink-0 overflow-hidden rounded-full bg-neutral-100 dark:bg-neutral-800',
          sizeClasses[size],
          className
        )}
        {...props}
      >
        {src ? (
          <img
            src={src}
            alt={alt || name || 'Avatar'}
            className="h-full w-full object-cover"
          />
        ) : (
          <span className="flex h-full w-full items-center justify-center font-medium text-neutral-600 dark:text-neutral-300 bg-neutral-200 dark:bg-neutral-700">
            {name ? getInitials(name) : '?'}
          </span>
        )}
      </div>
    );
  }
);

Avatar.displayName = 'Avatar';

export const AvatarGroup = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement> & { max?: number }>(
  ({ className, children, max = 5, ...props }, ref) => {
    const kids = Array.isArray(children) ? children : [children];
    const visibleChildren = kids.slice(0, max);
    const remainingCount = kids.length - max;

    return (
      <div ref={ref} className={cn('flex -space-x-2', className)} {...props}>
        {visibleChildren.map((child, index) => (
          <span key={index} className="relative z-10">
            {child}
          </span>
        ))}
        {remainingCount > 0 && (
          <span className="relative z-0 flex items-center justify-center rounded-full bg-neutral-100 dark:bg-neutral-800 border-2 border-white dark:border-neutral-900">
            <span className="text-xs font-medium text-neutral-600 dark:text-neutral-300 px-1">
              +{remainingCount}
            </span>
          </span>
        )}
      </div>
    );
  }
);

AvatarGroup.displayName = 'AvatarGroup';
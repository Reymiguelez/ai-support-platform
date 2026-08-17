import { User } from '@/types/auth';
import { Button } from '@/components/ui/Button';
import { Avatar } from '@/components/ui/Avatar';
import { DropdownMenu, DropdownMenuItem, DropdownMenuSeparator } from '@/components/ui/Dropdown';
import { Moon, Sun, User as UserIcon, Settings, LogOut, Bell } from 'lucide-react';
import { useTheme } from '@/context/ThemeContext';
import { useAuth } from '@/context/AuthContext';

interface HeaderProps {
  user: User;
}

export function Header({ user }: HeaderProps) {
  const { resolvedTheme, toggleTheme } = useTheme();
  const { logout } = useAuth();

  return (
    <header className="sticky top-0 z-20 h-16 bg-white/80 dark:bg-neutral-950/80 backdrop-blur-sm border-b border-neutral-200 dark:border-neutral-800">
      <div className="h-full px-4 lg:px-6 flex items-center justify-between gap-4">
        <div className="flex-1 lg:hidden">
          <h1 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">AI Support Platform</h1>
        </div>

        <div className="flex items-center gap-2 ml-auto">
          <DropdownMenu align="right">
            <Button
              variant="ghost"
              size="sm"
              className="relative p-2"
              aria-label="Notifications"
            >
              <Bell className="h-5 w-5 text-neutral-600 dark:text-neutral-400" />
              <span className="absolute top-1 right-1 h-4 w-4 rounded-full bg-red-500 text-[10px] font-medium text-white flex items-center justify-center">
                3
              </span>
            </Button>
            <DropdownMenuItem icon={<Bell className="h-4 w-4" />} onClick={() => {}}>Notifications</DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem icon={<Bell className="h-4 w-4" />} destructive onClick={() => {}}>Mark all as read</DropdownMenuItem>
          </DropdownMenu>

          <Button variant="ghost" size="sm" onClick={toggleTheme} aria-label={resolvedTheme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}>
            {resolvedTheme === 'dark' ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
          </Button>

          <DropdownMenu align="right">
            <Button variant="ghost" size="sm" className="gap-2 pr-3" aria-label="User menu">
              <Avatar name={user.full_name} src={user.avatar_url} size="sm" />
            </Button>
            <DropdownMenuItem icon={<UserIcon className="h-4 w-4" />} onClick={() => {}}>Profile</DropdownMenuItem>
            <DropdownMenuItem icon={<Settings className="h-4 w-4" />} onClick={() => {}}>Settings</DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem icon={<LogOut className="h-4 w-4" />} destructive onClick={logout}>Sign out</DropdownMenuItem>
          </DropdownMenu>
        </div>
      </div>
    </header>
  );
}
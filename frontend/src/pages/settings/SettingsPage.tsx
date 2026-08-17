import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useAuth } from '@/context/AuthContext';
import { useTheme } from '@/context/ThemeContext';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '@/components/ui/Card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/Tabs';
import { Badge } from '@/components/ui/Badge';
import { cn } from '@/utils/helpers';
import { User, Shield, Bell, Moon, Sun, Key, Save, Loader2, AlertCircle, CheckCircle } from 'lucide-react';

const profileSchema = z.object({
  full_name: z.string().min(2, 'Name must be at least 2 characters').max(100),
  username: z.string().min(3, 'Username must be at least 3 characters').max(50).regex(/^[a-zA-Z0-9_]+$/),
  email: z.string().email('Invalid email address'),
});

const passwordSchema = z.object({
  current_password: z.string().min(1, 'Current password is required'),
  new_password: z.string().min(8, 'Password must be at least 8 characters'),
  confirm_password: z.string(),
}).refine((data) => data.new_password === data.confirm_password, {
  message: 'Passwords do not match',
  path: ['confirm_password'],
});

type ProfileFormData = z.infer<typeof profileSchema>;
type PasswordFormData = z.infer<typeof passwordSchema>;

export function SettingsPage() {
  const { user, updateUser, isLoading: authLoading } = useAuth();
  const { theme, setTheme } = useTheme();

  const [profileMessage, setProfileMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [passwordMessage, setPasswordMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [isSavingProfile, setIsSavingProfile] = useState(false);
  const [isChangingPassword, setIsChangingPassword] = useState(false);

  const profileForm = useForm<ProfileFormData>({
    resolver: zodResolver(profileSchema),
    defaultValues: { full_name: user?.full_name || '', username: user?.username || '', email: user?.email || '' },
  });

  const passwordForm = useForm<PasswordFormData>({
    resolver: zodResolver(passwordSchema),
    defaultValues: { current_password: '', new_password: '', confirm_password: '' },
  });

  const onProfileSubmit = async (data: ProfileFormData) => {
    setIsSavingProfile(true);
    setProfileMessage(null);
    try {
      await updateUser({ full_name: data.full_name, username: data.username });
      setProfileMessage({ type: 'success', text: 'Profile updated successfully' });
    } catch (err: unknown) {
      setProfileMessage({ type: 'error', text: err instanceof Error ? err.message : 'Failed to update profile' });
    } finally {
      setIsSavingProfile(false);
    }
  };

  const onPasswordSubmit = async (data: PasswordFormData) => {
    setIsChangingPassword(true);
    setPasswordMessage(null);
    try {
      const response = await fetch('/api/v1/users/me/change-password', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('auth_tokens') ? JSON.parse(localStorage.getItem('auth_tokens')!).access_token : ''}`,
        },
        body: JSON.stringify({ current_password: data.current_password, new_password: data.new_password }),
      });
      if (!response.ok) throw new Error('Failed to change password');
      setPasswordMessage({ type: 'success', text: 'Password changed successfully' });
      passwordForm.reset();
    } catch (err: unknown) {
      setPasswordMessage({ type: 'error', text: err instanceof Error ? err.message : 'Failed to change password' });
    } finally {
      setIsChangingPassword(false);
    }
  };

  const handleThemeChange = (newTheme: 'light' | 'dark' | 'system') => {
    setTheme(newTheme);
  };

  return (
    <div className="flex-1 max-w-3xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-neutral-900 dark:text-neutral-100">Settings</h1>
        <p className="text-neutral-500 dark:text-neutral-400">Manage your account settings and preferences</p>
      </div>

      <Tabs defaultValue="profile">
        <TabsList>
          <TabsTrigger value="profile"><User className="h-4 w-4 mr-2" /> Profile</TabsTrigger>
          <TabsTrigger value="security"><Shield className="h-4 w-4 mr-2" /> Security</TabsTrigger>
          <TabsTrigger value="appearance"><Moon className="h-4 w-4 mr-2" /> Appearance</TabsTrigger>
          <TabsTrigger value="notifications"><Bell className="h-4 w-4 mr-2" /> Notifications</TabsTrigger>
        </TabsList>

        <TabsContent value="profile">
          <Card>
            <CardHeader>
              <CardTitle>Profile Information</CardTitle>
              <CardDescription>Update your personal information</CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={profileForm.handleSubmit(onProfileSubmit)} className="space-y-4">
                {profileMessage && (
                  <div className={cn('p-3 rounded-lg flex items-center gap-2 text-sm',
                    profileMessage.type === 'success' ? 'bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-400' : 'bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-400'
                  )}>
                    {profileMessage.type === 'success' ? <CheckCircle className="h-4 w-4" /> : <AlertCircle className="h-4 w-4" />}
                    {profileMessage.text}
                  </div>
                )}
                <div className="grid gap-4 md:grid-cols-2">
                  <Input label="Full Name" {...profileForm.register('full_name')} error={profileForm.formState.errors.full_name?.message} disabled={isSavingProfile || authLoading} />
                  <Input label="Username" {...profileForm.register('username')} error={profileForm.formState.errors.username?.message} disabled={isSavingProfile || authLoading} />
                </div>
                <Input label="Email" type="email" {...profileForm.register('email')} error={profileForm.formState.errors.email?.message} disabled={isSavingProfile || authLoading} />
                <CardFooter className="flex justify-end pt-0">
                  <Button type="submit" loading={isSavingProfile || authLoading}>
                    <Save className="h-4 w-4 mr-2" />
                    Save Changes
                  </Button>
                </CardFooter>
              </form>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="security">
          <Card>
            <CardHeader>
              <CardTitle>Change Password</CardTitle>
              <CardDescription>Update your password to keep your account secure</CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={passwordForm.handleSubmit(onPasswordSubmit)} className="space-y-4">
                {passwordMessage && (
                  <div className={cn('p-3 rounded-lg flex items-center gap-2 text-sm',
                    passwordMessage.type === 'success' ? 'bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-400' : 'bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-400'
                  )}>
                    {passwordMessage.type === 'success' ? <CheckCircle className="h-4 w-4" /> : <AlertCircle className="h-4 w-4" />}
                    {passwordMessage.text}
                  </div>
                )}
                <Input label="Current Password" type="password" {...passwordForm.register('current_password')} error={passwordForm.formState.errors.current_password?.message} disabled={isChangingPassword || authLoading} />
                <Input label="New Password" type="password" {...passwordForm.register('new_password')} error={passwordForm.formState.errors.new_password?.message} disabled={isChangingPassword || authLoading} helperText="Must be at least 8 characters" />
                <Input label="Confirm New Password" type="password" {...passwordForm.register('confirm_password')} error={passwordForm.formState.errors.confirm_password?.message} disabled={isChangingPassword || authLoading} />
                <CardFooter className="flex justify-end pt-0">
                  <Button type="submit" loading={isChangingPassword || authLoading}>
                    <Key className="h-4 w-4 mr-2" />
                    Change Password
                  </Button>
                </CardFooter>
              </form>
            </CardContent>
          </Card>

          <Card className="mt-6">
            <CardHeader>
              <CardTitle>Account Security</CardTitle>
              <CardDescription>Your current security status</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between p-4 rounded-lg bg-neutral-50 dark:bg-neutral-800">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-green-100 dark:bg-green-900/30"><Shield className="h-5 w-5 text-green-600" /></div>
                  <div><p className="font-medium">Two-Factor Authentication</p><p className="text-sm text-neutral-500">Add an extra layer of security</p></div>
                </div>
                <Badge variant="neutral">Not Enabled</Badge>
              </div>
              <div className="flex items-center justify-between p-4 rounded-lg bg-neutral-50 dark:bg-neutral-800">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-blue-100 dark:bg-blue-900/30"><Key className="h-5 w-5 text-blue-600" /></div>
                  <div><p className="font-medium">API Keys</p><p className="text-sm text-neutral-500">Manage your API access tokens</p></div>
                </div>
                <Button variant="outline" size="sm">Manage</Button>
              </div>
              <div className="flex items-center justify-between p-4 rounded-lg bg-neutral-50 dark:bg-neutral-800">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-purple-100 dark:bg-purple-900/30"><Loader2 className="h-5 w-5 text-purple-600" /></div>
                  <div><p className="font-medium">Active Sessions</p><p className="text-sm text-neutral-500">View and manage logged in devices</p></div>
                </div>
                <Button variant="outline" size="sm">View</Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="appearance">
          <Card>
            <CardHeader>
              <CardTitle>Appearance</CardTitle>
              <CardDescription>Customize how the application looks</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div>
                <label className="label">Theme</label>
                <div className="grid grid-cols-3 gap-3">
                  {[
                    { value: 'light' as const, label: 'Light', icon: Sun, desc: 'Always use light mode' },
                    { value: 'dark' as const, label: 'Dark', icon: Moon, desc: 'Always use dark mode' },
                    { value: 'system' as const, label: 'System', icon: <span className="text-xl">💻</span>, desc: 'Match system preference' },
                  ].map((option) => (
                    <button
                      key={option.value}
                      type="button"
                      onClick={() => handleThemeChange(option.value)}
                      className={cn(
                        'relative p-4 rounded-xl border-2 transition-all text-left',
                        theme === option.value
                          ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20'
                          : 'border-neutral-200 dark:border-neutral-700 hover:border-primary-300 dark:hover:border-primary-700'
                      )}
                    >
                      <div className="flex items-center gap-2 mb-1">
                        {typeof option.icon === 'function' ? <option.icon className="h-5 w-5" /> : option.icon}
                        <span className="font-medium">{option.label}</span>
                      </div>
                      <p className="text-xs text-neutral-500">{option.desc}</p>
                      {theme === option.value && (
                        <div className="absolute top-2 right-2 w-5 h-5 rounded-full bg-primary-500 flex items-center justify-center">
                          <CheckCircle className="h-3 w-3 text-white" />
                        </div>
                      )}
                    </button>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="notifications">
          <Card>
            <CardHeader>
              <CardTitle>Notifications</CardTitle>
              <CardDescription>Configure how you receive notifications</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {[
                { title: 'Email Notifications', desc: 'Receive email updates about your account', enabled: true },
                { title: 'Push Notifications', desc: 'Get browser notifications for new messages', enabled: false },
                { title: 'Weekly Digest', desc: 'Receive a weekly summary of activity', enabled: true },
                { title: 'Security Alerts', desc: 'Get notified about suspicious activity', enabled: true },
              ].map((item, i) => (
                <div key={i} className="flex items-center justify-between p-4 rounded-lg border border-neutral-200 dark:border-neutral-800">
                  <div><p className="font-medium">{item.title}</p><p className="text-sm text-neutral-500">{item.desc}</p></div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input type="checkbox" defaultChecked={item.enabled} className="sr-only peer" />
                    <div className="w-11 h-6 bg-neutral-300 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 dark:peer-focus:ring-primary-800 rounded-full peer dark:bg-neutral-600 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-neutral-600 peer-checked:bg-primary-600"></div>
                  </label>
                </div>
              ))}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
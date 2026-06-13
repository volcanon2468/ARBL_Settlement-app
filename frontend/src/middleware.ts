import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
  const token = request.cookies.get('auth_token')?.value;
  const { pathname } = request.nextUrl;
  const isPublicRoute = pathname === '/login' || pathname.startsWith('/api/v1/auth');

  let isExpired = false;
  if (token) {
    try {
      let payloadBase64 = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/');
      while (payloadBase64.length % 4) {
        payloadBase64 += '=';
      }
      const decodedPayload = JSON.parse(atob(payloadBase64));
      if (decodedPayload.exp && decodedPayload.exp * 1000 < Date.now()) {
        isExpired = true;
      }
    } catch (e) {
      isExpired = true;
    }
  }

  if (!isPublicRoute && (!token || isExpired)) {
    const response = NextResponse.redirect(new URL('/login', request.url));
    if (token) {
      response.cookies.delete('auth_token');
    }
    return response;
  }

  if (token && !isExpired && pathname === '/login') {
    return NextResponse.redirect(new URL('/settlement', request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
};

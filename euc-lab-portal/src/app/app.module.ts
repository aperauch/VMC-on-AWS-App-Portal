import { BrowserModule } from '@angular/platform-browser';
import { NgModule } from '@angular/core';
import { AppRoutingModule } from './app-routing.module';
import { AppComponent } from './app.component';
import { ClarityModule } from '@clr/angular';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { HomeComponent } from './components/home/home.component';
import { DnsComponent } from './components/dns/dns.component';
import { LoggerModule, NgxLoggerLevel } from 'ngx-logger';
import { FormsModule } from '@angular/forms';
import { ReactiveFormsModule } from '@angular/forms';
import { HttpClientModule, HTTP_INTERCEPTORS } from '@angular/common/http';
import { ErrorInterceptorService } from './services/error/error-interceptor.service';
import { MatDialogModule } from '@angular/material/dialog';
import { PublicIpsComponent } from './components/public-ips/public-ips.component';
import { NatRulesComponent } from './components/nat-rules/nat-rules.component';
import { CgwRulesComponent } from './components/cgw-rules/cgw-rules.component';
import { LoginComponent } from './components/login/login.component';
import { LayoutComponent } from './components/layout/layout.component';
import { JwtInterceptor } from './services';
import { WebCertificatesComponent } from './components/web-certificates/web-certificates.component';

@NgModule({
    declarations: [
        HomeComponent,
        DnsComponent,
        PublicIpsComponent,
        NatRulesComponent,
        CgwRulesComponent,
        AppComponent,
        LayoutComponent,
        LoginComponent,
        WebCertificatesComponent
    ],
    imports: [
        BrowserModule,
        ClarityModule,
        HttpClientModule,
        BrowserAnimationsModule,
        MatDialogModule,
        FormsModule,
        ReactiveFormsModule,
        AppRoutingModule,
        LoggerModule.forRoot({ serverLoggingUrl: '/logs', level: NgxLoggerLevel.DEBUG, serverLogLevel: NgxLoggerLevel.ERROR })
    ],
    providers: [
        { provide: HTTP_INTERCEPTORS, useClass: ErrorInterceptorService, multi: true },
        { provide: HTTP_INTERCEPTORS, useClass: JwtInterceptor, multi: true }
    ],
    bootstrap: [AppComponent]
})
export class AppModule { }

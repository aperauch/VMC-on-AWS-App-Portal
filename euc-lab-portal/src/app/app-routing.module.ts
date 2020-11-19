import { NgModule } from '@angular/core';
import { Routes, RouterModule } from '@angular/router';
import { AppComponent } from './app.component';
import { CgwRulesComponent } from './components/cgw-rules/cgw-rules.component';
import { DnsComponent } from './components/dns/dns.component';
import { HomeComponent } from './components/home/home.component';
import { LayoutComponent } from './components/layout/layout.component';
import { LoginComponent } from './components/login/login.component';
import { NatRulesComponent } from './components/nat-rules/nat-rules.component';
import { PublicIpsComponent } from './components/public-ips/public-ips.component';
import { WebCertificatesComponent } from './components/web-certificates/web-certificates.component';
import { AuthGuard } from './helpers/auth.guard';

const routes: Routes = [
    { path: '', component: LayoutComponent,
        children: [
            { path: '', component: HomeComponent, canActivate: [AuthGuard] },
            { path: 'home', component: HomeComponent, canActivate: [AuthGuard] },
            { path: 'dns', component: DnsComponent, canActivate: [AuthGuard] },
            { path: 'publicips', component: PublicIpsComponent, canActivate: [AuthGuard] },
            { path: 'natrules', component: NatRulesComponent, canActivate: [AuthGuard] },
            { path: 'cgwrules', component: CgwRulesComponent, canActivate: [AuthGuard] },
            { path: 'certificates', component: WebCertificatesComponent, canActivate: [AuthGuard] }
        ]
    },
    { path: 'login', component: LoginComponent },
    { path: '**', redirectTo: '' }
];

@NgModule({
    imports: [RouterModule.forRoot(routes)],
    exports: [RouterModule]
})
export class AppRoutingModule { }

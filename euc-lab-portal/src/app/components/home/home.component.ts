import { Component, OnInit } from '@angular/core';
import { ApiClientService } from '../../services/api/api-client.service';

@Component({
  selector: 'app-home',
  templateUrl: './home.component.html',
  styleUrls: ['./home.component.scss']
})
export class HomeComponent implements OnInit {

  constructor(
    private apiClient: ApiClientService
  ) { }

  ngOnInit(): void {
  }

}

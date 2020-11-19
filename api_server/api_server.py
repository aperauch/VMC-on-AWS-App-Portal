import logging, sys, os, ldap, time, yaml
from ns1 import NS1, Config
from ns1.rest.errors import ResourceException, RateLimitException, AuthException
from flask import Flask, json, g, request, make_response, jsonify
from flask.logging import create_logger
from flask_cors import CORS, cross_origin
from flask_jwt import JWT, jwt_required, current_identity
from datetime import datetime, timedelta
from vmware.vapi.vmc.client import create_vmc_client
from com.vmware.nsx_vmc_app_client_for_vmc import create_nsx_vmc_app_client_for_vmc
from com.vmware.nsx_policy_client_for_vmc import create_nsx_policy_client_for_vmc
from com.vmware.nsx_vmc_app.model_client import PublicIp
from com.vmware.nsx_policy.model_client import PolicyNatRule
from vmware.vapi.bindings.struct import PrettyPrinter as NsxPrettyPrinter
from com.vmware.nsx_policy.model_client import ApiError

# Import config settings from yaml file
yaml_file = open("e:\\GitHub\\EUC-Lab-Portal-Python\\api_server\\config.yaml", 'r')
yaml_dict = yaml.load(yaml_file, Loader=yaml.FullLoader)

# Logging Settings
log_format = ('[%(asctime)s] %(levelname)-8s %(name)-12s %(message)s')
logging.basicConfig(
    filename=yaml_dict['LogFilepath'], 
    level=logging.ERROR,
    format=log_format
)

# Flask app config settings
app = Flask(__name__)
app.config['CORS_HEADERS'] = 'Content-Type'
app.config['JWT_AUTH_HEADER_PREFIX'] = 'Bearer'
app.config['JWT_EXPIRATION_DELTA'] = timedelta(seconds=yaml_dict['JwtTimeoutInSeconds'])
app.config['SECRET_KEY'] = yaml_dict['JwtKey']
CORS(app)

# LDAP
LDAP_CONNECTION_STRING = yaml_dict['LdapConnectionString']
LDAP_PROTOCOL_VERSION = yaml_dict['LdapProtocolVersion']

# NS1 DNS config settings
API_KEY_VALUE = yaml_dict['DnsApiKey']
EUCLABNET_ZONE_NAME = yaml_dict['DnsZones'][0]
PSOLABNET_ZONE_NAME = yaml_dict['DnsZones'][1]
config = Config()
config.createFromAPIKey(API_KEY_VALUE)
api = NS1(config=config)

# VMC
VMC_CSP_REFRESH_TOKEN = yaml_dict['VmcCspRefreshToken']
VMC_CSP_AUTH_URL = yaml_dict['VmcCspAuthUrl'] + "?refresh_token=" + VMC_CSP_REFRESH_TOKEN
VMC_ORG = yaml_dict['VmcOrg']
VMC_ORG_ID = yaml_dict['VmcOrgId']
VMC_SDDC = yaml_dict['VmcSddc']
VMC_SDDC_ID = yaml_dict['VmcSddcId']
NSX_VMC_AWS_API_BASE_URL = yaml_dict['NsxVmxAwsApiBaseUrl']

# format NSXT objects for readability
nsx_pp = NsxPrettyPrinter()

@app.route("/")
def home():
    localtime = time.asctime( time.localtime(time.time()) )
    logging.info("Server is running.")
    return {"Status": "Running", "DateTime": localtime}

@app.route("/dns", methods=["GET"])
@jwt_required()
def get_dns_records():

    try:
        psolabnet_zone = api.loadZone(PSOLABNET_ZONE_NAME)
        euclabnet_zone = api.loadZone(EUCLABNET_ZONE_NAME)

        all_zone_records =  {
            psolabnet_zone.zone: psolabnet_zone.data["records"],
            euclabnet_zone.zone: euclabnet_zone.data["records"]
        }
        all_zone_records_json = json.dumps(all_zone_records)
        
        return all_zone_records_json
    except Exception as ex:
        logging.error("Exception:  " + ex)

    response = make_response({"message": "No action was taken."}, 500)
    response.headers["Content-Type"] = "application/json"
    return response
    

@app.route("/dns", methods=["PUT"])
@jwt_required()
def create_dns_record():
    data = request.get_json()
    logging.info("Creating DNS record " + data['zone'])

    zone = api.loadZone(data['zone'])

    response = make_response({"message": "No action was taken."}, 500)

    try:
        if data['type'] == 'A':
            ns1Record = zone.add_A(data['domain'], data['answers'])
            json = jsonify(ns1Record.data)
            response = make_response(ns1Record.data, json.status_code)
        elif data['type'] == 'AAAA':
            ns1Record = zone.add_AAAA(data['domain'], data['answers'])
            json = jsonify(ns1Record.data)
            response = make_response(ns1Record.data, json.status_code)
        elif data['type'] == 'CNAME':
            ns1Record = zone.add_CNAME(data['domain'], data['answers'])
            json = jsonify(ns1Record.data)
            response = make_response(ns1Record.data, json.status_code)
        elif data['type'] == 'MX':
            mx_answers_list = data['answers'].replace(" ","").split(",")
            if len(mx_answers_list) == 2:
                ns1Record = zone.add_MX(data['domain'], [[int(mx_answers_list[0]), mx_answers_list[1]]])
                json = jsonify(ns1Record.data)
                response = make_response(ns1Record.data, json.status_code)
            elif len(mx_answers_list) == 4:
                ns1Record = zone.add_MX(data['domain'], [[int(mx_answers_list[0]), mx_answers_list[1]], [int(mx_answers_list[2]), mx_answers_list[3]]])
                json = jsonify(ns1Record.data)
                response = make_response(ns1Record.data, json.status_code)
            else:
                response = make_response({"message": "Unable to create MX record due to issue parsing the answers list => " + data['answers']}, 400)

        elif data['type'] == 'TXT':
            ns1Record = zone.add_TXT(data['domain'], data['answers'])
            json = jsonify(ns1Record.data)
            response = make_response(ns1Record.data, json.status_code)
        else:
            logging.warn("Unknown record type: " + data['type'])
            response = make_response({"message": "Unable to create DNS record due to unknown record type " + data['type']}, 400)

    except ResourceException as re:
        response = make_response(re.response.text, re.response.status_code)
        logging.error("ResourceException:  " + re)
    except Exception as ex:
        logging.error("Exception:  " + ex)
        response = make_response({"message": "An error occurred when trying to create a DNS record."}, 500)

    response.headers["Content-Type"] = "application/json"
    return response

@app.route("/dns", methods=["POST"])
@jwt_required()
def update_dns_record():
    data = request.get_json()
    zone = api.loadZone(data['zone'])
    rec = zone.loadRecord(data['domain'], data['type'])

    # Modify the record with the new values
    logging.info("Updating DNS record: " + rec.domain)

    response = make_response({"message": "No action was taken."}, 500)
    
    try:
        ns1Record = rec.update(answers=[data['answers']])
        json = jsonify(ns1Record.data)
        response = make_response(ns1Record.data, json.status_code)
    except ResourceException as re:
        response = make_response(re.response.text, re.response.status_code)
        logging.error("ResourceException:  " + ex)
    except Exception as ex:
        logging.error("Exception:  " + ex)
        error_message = "Something unexpected occurred when updating " + rec.domain
        response = make_response(jsonify({"message": error_message}), 500)
    
    response.headers["Content-Type"] = "application/json"
    return response


@app.route("/dns/delete", methods=["POST"])
@jwt_required()
def delete_dns_record():
    response = make_response({"message": "No action was taken."}, 500)

    try:
        data = request.get_json()
        zone = api.loadZone(data['zone'])
        rec = zone.loadRecord(data['domain'], data['type'])
        print("Deleting DNS record: " + rec.domain)
        response = rec.delete()

        if response:
            error_message = "Something unexpected occurred when deleting " + rec.domain
            print(error_message)
            response = make_response(jsonify({"message": error_message}), 500)
        else:
            print("Deleted " + rec.domain + " successfully.")
            response = make_response(jsonify({"message": "Deleted " + rec.domain + " successfully."}))
            
    except Exception as ex:
        logging.error("Exception:  " + ex)
        log_error(ex)
        error_message = "Something unexpected occurred when deleting DNS record IP " + data['domain']
        response = make_response(jsonify({"message": error_message}), 500)

    response.headers["Content-Type"] = "application/json"
    return response

@app.route("/publicips", methods=["GET"])
@jwt_required()
def get_vmc_public_ips():
    response = make_response({"message": "No action was taken."}, 500)

    try:
        nsx_vmc_client = create_nsx_vmc_app_client_for_vmc(VMC_CSP_REFRESH_TOKEN, VMC_ORG_ID, VMC_SDDC_ID)
        response = make_response(nsx_vmc_client.infra.PublicIps.list().to_json(), 200)
    except Exception as ex:
        logging.error("Exception:  " + ex)
        log_error(ex)
        error_message = "Something unexpected occurred when getting list of leased IP addresses."
        response = make_response(jsonify({"message": error_message}), 500)

    response.headers["Content-Type"] = "application/json"
    return response

@app.route("/publicips", methods=["POST"])
@jwt_required()
def request_new_vmc_public_ip():
    response = make_response({"message": "No action was taken."}, 500)

    try:
        nsx_vmc_client = create_nsx_vmc_app_client_for_vmc(VMC_CSP_REFRESH_TOKEN, VMC_ORG_ID, VMC_SDDC_ID)
        
        data = request.get_json()
        public_ip = PublicIp(display_name=data['display_name'])

        response = make_response(nsx_vmc_client.infra.PublicIps.update(data['display_name'], public_ip).to_json(), 200)
    except Exception as ex:
        logging.error("Exception:  " + ex)
        log_error(ex)
        error_message = "Something unexpected occurred when requesting IP " + data['display_name']
        response = make_response(jsonify({"message": error_message}), 500)

    response.headers["Content-Type"] = "application/json"
    return response

@app.route("/publicips", methods=["PATCH"])
@jwt_required()
def update_vmc_public_ip():
    nsx_vmc_client = create_nsx_vmc_app_client_for_vmc(VMC_CSP_REFRESH_TOKEN, VMC_ORG_ID, VMC_SDDC_ID)
    
    data = request.get_json()
    public_ip = PublicIp(display_name=data['display_name'], ip=data['ip'], id=data['id'])

    response = make_response(nsx_vmc_client.infra.PublicIps.update(data['display_name'], public_ip).to_json(), 200)
    response.headers["Content-Type"] = "application/json"
    
    return response

@app.route("/publicips", methods=["PUT"])
@jwt_required()
def delete_new_vmc_public_ip():
    response = make_response({"message": "No action was taken."}, 500)

    try:
        data = request.get_json()

        # Ensure IP is not being used in a NAT Rule before attempting delete
        nsx_policy_client = create_nsx_policy_client_for_vmc(VMC_CSP_REFRESH_TOKEN, VMC_ORG_ID, VMC_SDDC_ID)
        nat = nsx_policy_client.infra.tier_1s.nat.NatRules.list('cgw', 'USER')

        for nat_rule in nat.results:
            if nat_rule.translated_network == data['ip']:
                response = make_response({"message": "The IP is being used by NAT rule " + nat_rule.display_name + ".  Delete NAT rule before continuing." }, 409)
                response.headers["Content-Type"] = "application/json"
                return response

        # Proceed to delete
        nsx_vmc_client = create_nsx_vmc_app_client_for_vmc(VMC_CSP_REFRESH_TOKEN, VMC_ORG_ID, VMC_SDDC_ID)
        response = nsx_vmc_client.infra.PublicIps.delete(data['display_name']) # None value returned on successful delete
        response = make_response()
    except Exception as ex:
        logging.error("Exception:  " + ex)
        log_error(ex)
        error_message = "Something unexpected occurred when releasing IP " + data['ip']
        response = make_response(jsonify({"message": error_message}), 500)
        
    response.headers["Content-Type"] = "application/json"
    return response

@app.route("/natrules", methods=['GET'])
@jwt_required()
def get_nat_rules():
    response = make_response({"message": "No action was taken."}, 500)

    try:
        nsx_policy_client = create_nsx_policy_client_for_vmc(VMC_CSP_REFRESH_TOKEN, VMC_ORG_ID, VMC_SDDC_ID)
        nat = nsx_policy_client.infra.tier_1s.nat.NatRules.list('cgw', 'USER')
        response = make_response(nat.to_json(), 200)
    except Exception as ex:
        logging.error("Exception:  " + ex)
        log_error(ex)
        error_message = "Something unexpected occurred when getting NAT rules.  Exception: " + ex
        response = make_response(jsonify({"message": error_message}), 500)

    response.headers["Content-Type"] = "application/json"
    return response

@app.route("/natrules", methods=['POST'])
@jwt_required()
def create_nat_rule():
    data = request.get_json()
    response = make_response({"message": "No action was taken."}, 500)

    try:
        nat_obj = PolicyNatRule(action = 'REFLEXIVE',
                                scope = ['/infra/labels/cgw-public'],
                                source_network = data['source_network'],
                                translated_network = data['translated_network'],
                                display_name = data['display_name'], 
                                sequence_number = 1,
                                firewall_match = 'MATCH_INTERNAL_ADDRESS')

        # patch() method is void
        nsx_policy_client = create_nsx_policy_client_for_vmc(VMC_CSP_REFRESH_TOKEN, VMC_ORG_ID, VMC_SDDC_ID)
        nsx_policy_client.infra.tier_1s.nat.NatRules.patch('cgw', 'USER', data['display_name'], nat_obj) 
        response = make_response(nat_obj.to_json(), 200)    
    except Exception as ex:
        logging.error("Exception:  " + ex)
        log_error(ex)
        error_message = "Something unexpected occurred when creating NAT rule " + data['display_name'] + ". Exception: " + ex
        response = make_response(jsonify({"message": error_message}), 500)

    response.headers["Content-Type"] = "application/json"
    return response

@app.route("/natrules", methods=['PUT'])
@jwt_required()
def delete_nat_rule():
    data = request.get_json()
    response = make_response({"message": "No action was taken."}, 500)

    try:
        nsx_policy_client = create_nsx_policy_client_for_vmc(VMC_CSP_REFRESH_TOKEN, VMC_ORG_ID, VMC_SDDC_ID)
        nsx_policy_client.infra.tier_1s.nat.NatRules.delete('cgw', 'USER', data['display_name'])
        response = make_response({"message": "Successfully deleted NAT rule " + data['display_name']}, 200)
    except Exception as ex:
        logging.error("Exception:  " + ex)
        log_error(ex)
        error_message = "Something unexpected occurred when deleting NAT rule " + data['display_name'] + ". Exception: " + ex
        response = make_response(jsonify({"message": error_message}), 500)

    response.headers["Content-Type"] = "application/json"
    return response

@app.route("/cgwrules", methods=['GET'])
@jwt_required()
def get_cgw_rules():
    response = make_response({"message": "No action was taken."}, 500)

    try:
        nsx_policy_client = create_nsx_policy_client_for_vmc(VMC_CSP_REFRESH_TOKEN, VMC_ORG_ID, VMC_SDDC_ID)
        cgw_object = nsx_policy_client.infra.domains.GatewayPolicies.get('cgw', 'default')
        
        security_groups = nsx_policy_client.infra.domains.Groups.list('cgw').results
        services = nsx_policy_client.infra.Services.list()

        # Replace destination group ID, source group ID, and service ID with display name
        for cgw in cgw_object.rules:
            
            new_dest_list = []
            for dest_group in cgw.destination_groups:
                if dest_group != 'ANY':
                    for sec_group in security_groups:
                        if sec_group.id == dest_group.split('/')[-1]:
                            new_dest_list.append(sec_group.display_name)
                
            if len(new_dest_list) > 0:
                cgw.destination_groups = new_dest_list

            new_source_list = []
            for source_group in cgw.source_groups:
                if source_group != 'ANY':
                    for sec_group in security_groups:
                        if sec_group.id == source_group.split('/')[-1]:
                            new_source_list.append(sec_group.display_name)

            if len(new_source_list) > 0:
                cgw.source_groups = new_source_list
            
            new_service_list = []
            for cgw_service in cgw.services:
                if cgw_service != 'ANY':
                    for service in services.results:
                        if service.id == cgw_service.split('/')[-1]:
                            new_service_list.append(service.display_name)
                    
            if len(new_service_list) > 0:
                cgw.services = new_service_list

            new_scope_list = []
            for scope in cgw.scope:
                new_scope_list.append(scope.split('/')[-1])
            if len(new_scope_list) > 0:
                cgw.scope = new_scope_list


        response = make_response(cgw_object.to_json(), 200)
    except Exception as ex:
        logging.error("Exception:  " + ex)
        log_error(ex)
        error_message = "Something unexpected occurred when getting CGW rules.  Exception: " + ex
        response = make_response(jsonify({"message": error_message}), 500)
        
    response.headers["Content-Type"] = "application/json"
    return response

@app.route("/cgwrules", methods=['PUT'])
@jwt_required()
def delete_cgw_rule():
    data = request.get_json()
    response = make_response({"message": "No action was taken."}, 500)
    try:
        nsx_policy_client = create_nsx_policy_client_for_vmc(VMC_CSP_REFRESH_TOKEN, VMC_ORG_ID, VMC_SDDC_ID)
        nsx_policy_client.infra.domains.gateway_policies.Rules.delete('cgw', 'default', data['display_name'])
        response = make_response({"message": "Successfully deleted CGW rule " + data['display_name']}, 200)
    except Exception as ex:
        logging.error("Exception:  " + ex)
        log_error(ex)
        error_message = "Something unexpected occurred when deleting CGW rule " + data['display_name'] + ". Exception: " + ex
        response = make_response(jsonify({"message": error_message}), 500)

    response.headers["Content-Type"] = "application/json"
    return response

def log_error(ex):
    """
    Generic error logger that will use NSXT API Error message decoders for
    more descriptive information on errors
    """

    api_error = ex.data.convert_to(ApiError)
    print("Error configuring {}".format(api_error.error_message))
    print("{}".format(api_error.__dict__))
    print("{}".format(api_error.details))

    logging.error("Error configuring {}".format(api_error.error_message))
    logging.error("{}".format(api_error.__dict__))
    logging.error("{}".format(api_error.details))

def ldap_bind_as_user(upn, password):
    """
    UPN is required for AD bind.
    """
    
    result = False
    conn = ldap.initialize(LDAP_CONNECTION_STRING)
    conn.protocol_version = LDAP_PROTOCOL_VERSION
    
    try:
        bind_result_s = conn.simple_bind_s(upn, password)
        if bind_result_s[0] == 97:
            logging.info("LDAP bind successful for upn " + upn + ".")
            result = User(id=upn)
        else:
            logging.error("Received an unexpected bind result code: " + bind_result_s)

    except ldap.INVALID_CREDENTIALS:
        logging.error("Username or password is incorrect.")
    except ldap.LDAPError as e:
        if type(e.message) == dict and e.message.has_key('desc'):
            logging.error("LDAP Error exception occurred:  " +  e.message['desc'])
        else:
            logging.error("A server error occurred during API authentication.")
    except Exception as e:
        logging.error("An exception occurred when performing ldap bind.  Exception:  " + e)
        
    finally:
        conn.unbind_s()

    return result


class User(object):
    def __init__(self, id):
        self.id = id

def __str__(self):
    return "User(id='%s')" % self.id

def authenticate(username, password):
    if not (username and password):
        return False
    elif "_admin" not in username:
        logging.error("The given username does not contain the substring '_admin':  " + username)
        return False
    else:
        return ldap_bind_as_user(username, password)
    
def identity(payload):
    user_id = payload['identity']
    return {"user_id": user_id}

jwt = JWT(app, authenticate, identity)

if __name__ == "__main__":
    app.run()
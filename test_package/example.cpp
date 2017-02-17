#include <stdio.h>
#include <stdlib.h>

#include <gnutls/gnutls.h>

#include <iostream>

using namespace std;

void testGnutls();

int main(){
    cout << "********* Testing gnutls *********" << endl;
    testGnutls();
    cout << "**********************************" << endl;

    return 0;
}

void testGnutls(){
    if (gnutls_check_version("3.1.4") == NULL) {
            fprintf(stderr, "GnuTLS 3.1.4 or later is required for this example\n");
            exit(1);
    }

    /* for backwards compatibility with gnutls < 3.3.0 */
    gnutls_global_init();

    gnutls_session_t session;

    printf("init session\n");
    gnutls_init(&session, GNUTLS_SERVER);

    printf("end session\n");
    gnutls_deinit(session);

    gnutls_global_deinit();
}

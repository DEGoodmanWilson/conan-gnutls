#!/usr/bin/env python
# -*- coding: utf-8 -*-

from conans import ConanFile, AutoToolsBuildEnvironment, tools
import os


class GnutlsConan(ConanFile):
    name = "gnutls"
    version = "3.6.2"
    url = "http://github.com/DEGoodmanWilson/conan-gmp"
    description = "The GNU TLS library"
    license = "https://www.gnutls.org/manual/html_node/Copying-Information.html#Copying-Information"
    settings =  "os", "compiler", "arch", "build_type"
    options = {"shared": [True, False],
               "enable-m-guard": [True, False],
               "disable-asm": [True, False],
               "enable-ld-version-script": [True, False],
               "disable-endian-check": [True, False],
               "enable-random-daemon": [True, False],
               "enable-hmac-binary-check": [True, False],
               "disable-padlock-support": [True, False],
               "disable-aesni-support": [True, False],
               "disable-O-flag-munging": [True, False]}
               #TODO add in non-binary flags
    default_options = "shared=False", "enable-m-guard=False", "disable-asm=False", \
                      "enable-ld-version-script=False", "disable-endian-check=False", \
                      "enable-random-daemon=False", "disable-aesni-support=False", \
              "enable-hmac-binary-check=False", "disable-padlock-support=False", "disable-O-flag-munging=False"
    requires = 'libiconv/1.15@bincrafters/stable', 'nettle/3.4@DEGoodmanWilson/stable', 'gmp/6.1.1@DEGoodmanWilson/stable', 'zlib/1.2.8@conan/stable'
    # TODO add p11-kit http://p11-glue.freedesktop.org/p11-kit.html and libidn and libdane


    def source(self):
        zip_name = "gnutls-{0}.tar.gz".format(self.version)
        tools.download("https://www.dropbox.com/s/r477opmxmhhee5g/{0}?dl=1".format(zip_name), zip_name)
        # zip_name = "gnutls-{0}.tar.xz".format(self.version)
        # tools.download("https://www.gnupg.org/ftp/gcrypt/gnutls/v{0}/{1}".format(".".join(self.version.split(".")[0:2]), zip_name), zip_name)
        tools.untargz(zip_name)
        os.unlink(zip_name)

        extracted_dir = self.name + "-" + self.version
        os.rename(extracted_dir, "sources")

    def ugly_env_configure_vars(self, verbose=False):
        """Reusable in any lib with configure!!"""
    
        # find nettle and hogweed paths
        nettle_lib_path = ""
        nettle_include_path = ""
        gmp_lib_path = ""
        gmp_include_path = ""
        for path in self.deps_cpp_info.lib_paths:
            if "nettle" in path:
                nettle_lib_path = path
            elif "gmp" in path:
                gmp_lib_path = path

        for path in self.deps_cpp_info.include_paths:
            if "nettle" in path:
                nettle_include_path = path
            elif "gmp" in path:
                gmp_include_path = path


        package_flags = {
            'NETTLE_CFLAGS': "-I{0}".format(nettle_include_path),
            'NETTLE_LIBS': "-L{0} -lnettle".format(nettle_lib_path),
            'HOGWEED_CFLAGS': "-I{0}".format(nettle_include_path),
            'HOGWEED_LIBS': "-L{0} -lhogweed".format(nettle_lib_path),
            'GMP_CFLAGS': "-I{0}".format(gmp_include_path),
            'GMP_LIBS': "-L{0} -lgmp".format(gmp_lib_path)
        }
        return package_flags

    def build(self):
        if self.settings.compiler == 'Visual Studio':
            # self.build_vs()
            self.output.fatal("No windows support yet. Sorry. Help a fellow out and contribute back?")


        with tools.chdir("sources"):
            with tools.environment_append(self.ugly_env_configure_vars()):

                env_build = AutoToolsBuildEnvironment(self)
                env_build.fpic = True

                print os.environ
                print os.listdir(os.environ['NETTLE_LIBS'].split('-L')[-1].split(' -l')[0])

                config_args = []
                for option_name in self.options.values.fields:
                    if(option_name == "shared"):
                        if(getattr(self.options, "shared")):
                            config_args.append("--enable-shared")
                            config_args.append("--disable-static")
                        else:
                            config_args.append("--enable-static")
                            config_args.append("--disable-shared")
                    else:
                        activated = getattr(self.options, option_name)
                        if activated:
                            self.output.info("Activated option! %s" % option_name)
                            config_args.append("--%s" % option_name)

                # TODO we can do better.
                config_args.append("--without-p11-kit")
                config_args.append("--without-idn")
                config_args.append("--with-included-libtasn1")
                config_args.append("--enable-local-libopts")
                config_args.append("--with-included-unistring")

                iconv_prefix = ""
                for path in self.deps_cpp_info.lib_paths:
                    if "iconv" in path:
                        iconv_prefix = '/lib'.join(path.split("/lib")[0:-1]) #remove the final /lib. There are probably better ways to do this.
                        break
                config_args.append("--with-libiconv-prefix={0}".format(iconv_prefix))

                env_build.configure(args=config_args)
                env_build.make()

    def package(self):
        self.copy(pattern="COPYING*", src="sources")
        self.copy(pattern="*.h", dst="include", src="sources")
        # self.copy(pattern="*.dll", dst="bin", src="bin", keep_path=False)
        self.copy(pattern="*.lib", dst="lib", src="sources/.libs", keep_path=False)
        self.copy(pattern="*.a", dst="lib", src="sources/.libs", keep_path=False)
        self.copy(pattern="*.so*", dst="lib", src="sources/.libs", keep_path=False)
        self.copy(pattern="*.dylib", dst="lib", src="sources/.libs", keep_path=False)

        
    def package_info(self):
        self.cpp_info.libs = tools.collect_libs(self)



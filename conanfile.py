from conans import ConanFile
from conans.tools import download, pythonpath
from conans import tools

import os
from os import path

class GnutlsConan(ConanFile):
    name        = "gnutls"
    version     = "3.5.11"
    license     = "LGPLv2.1+"
    description = "a secure communications library for SSL, TLS and DTLS protocols and technologies around them"
    url = "http://github.com/DEGoodmanWilson/conan-gnutls"

    settings =  "os", "compiler", "arch"
    options = {
        "shared": [True, False],
        "enable_m_guard": [True, False],
        "disable_asm": [True, False],
        "enable_ld_version_script": [True, False],
        "disable_endian_check": [True, False],
        "enable_random_daemon": [True, False],
        "enable_hmac_binary_check": [True, False],
        "disable_padlock_support": [True, False],
        "disable_aesni_support": [True, False],
        "disable_O_flag_munging": [True, False]
    } #TODO add in non-binary flags

    default_options = (
        "shared=False",
        "enable_m_guard=False",
        "disable_asm=False",
        "enable_ld_version_script=False",
        "disable_endian_check=False",
        "enable_random_daemon=False",
        "disable_aesni_support=False",
        "enable_hmac_binary_check=False",
        "disable_padlock_support=False",
        "disable_O_flag_munging=False"
    )

    requires = (
        'libiconv/1.14@lasote/stable',
        'nettle/3.3@DEGoodmanWilson/testing',
        'gmp/6.1.2@DEGoodmanWilson/testing',
        'zlib/1.2.8@lasote/stable',

        "AutotoolsHelper/0.0.2@noface/experimental"
    )
    # TODO add p11-kit http://p11-glue.freedesktop.org/p11-kit.html and libidn and libdane

    ZIP_FOLDER_NAME = "gnutls-%s" % version

    SHA256 = "51765cc5579e250da77fbd7871507c517d01b15353cc40af7b67e9ec7b6fe28f"

    def source(self):
        zip_name = "gnutls-%s.tar.xz" % self.version
        download("https://www.gnupg.org/ftp/gcrypt/gnutls/v3.5/%s" % zip_name, zip_name)
#        self.download_ftp("ftp://ftp.gnutls.org/gcrypt/gnutls/v3.4/%s" % zip_name, zip_name)
        tools.check_sha256(zip_name, self.SHA256)
        #tools.untargz(zip_name)
        self.uncompress_xz(zip_name)
        
    def configure(self):
        del self.settings.compiler.libcxx

    def build(self):
        if self.settings.os == "Windows":
            # gnutls itself work on windows. So if the build is broken, let windows
            # users help to fix
            self.output.warn("May not work on Windows!")

        self.prepare_build()
        self.configure_and_make()
            
    def package(self):
        SRC = self.ZIP_FOLDER_NAME

        self.copy("*.h", dst="include", src=path.join(SRC, "src"), keep_path=True)
        self.copy("*.h", dst="include", src=path.join(SRC, "lib", "includes"), keep_path=True)
        if self.options.shared:
            self.copy(pattern="*.so*", dst="lib", src=SRC, keep_path=False)
            self.copy(pattern="*.dll*", dst="bin", src=SRC, keep_path=False)
        else:
            self.copy(pattern="*.a", dst="lib", src=SRC, keep_path=False)

        self.copy(pattern="*.lib", dst="lib", src=SRC, keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ['gnutls']

    ##################################################################################################

    def prepare_build(self):
        if getattr(self, "package_folder", None) is None:
            self.package_folder = path.abspath(path.join(".", "install"))
            self._try_make_dir(self.package_folder)

    def configure_and_make(self):
        with tools.chdir(self.ZIP_FOLDER_NAME), pythonpath(self):
            from autotools_helper import Autotools

            autot = Autotools(self,
               shared      = self.options.shared)

            self.autotools_build(autot)

    def autotools_build(self, autot):
        self.add_options(autot)

        # TODO remove --without-p11-kit
        autot.without_feature("p11-kit")
        autot.without_feature("idn")
        autot.with_feature("included-libtasn1")
        autot.with_feature("included-unistring")
#        autot.options["with-included-unistring"] = ""
        #autot.with_feature("libiconv-prefix=" + iconv_prefix)
        autot.enable("local-libopts")

        extra_env = self.make_env()

        with tools.environment_append(extra_env):
            autot.configure()
            autot.build()
            autot.install()

    def add_options(self, autot):
        for option_name in self.options.values.fields:
            if not getattr(self.options, option_name) or option_name == "shared":
                continue

            self.output.info("Activate option: %s" % option_name)

            opt = option_name.replace("_", "-").split("-", 1)

            if opt[0] == "enable":
                autot.enable(opt[1])
            elif opt[0] == "disable":
                autot.enable(opt[1])

    def make_env(self):
        env = {}

        self.make_pkg_config_env(env, "nettle")

        env["HOGWEED_CFLAGS"] = env["NETTLE_CFLAGS"]
        env["HOGWEED_LIBS"] = env["NETTLE_LIBS"]

        return env

    def make_pkg_config_env(self, env, dep_name, **args):
        deps = self.deps_cpp_info[dep_name]
        CFLAGS = " -I".join([""] + deps.include_paths)
        LIBS   = " -L".join([""] + deps.lib_paths)
        LIBS  += " -l".join([""] + args.get('libs', deps.libs))

        env[dep_name.upper() + '_CFLAGS'] = CFLAGS
        env[dep_name.upper() + '_LIBS']   = LIBS

        self.output.info("env for %s: CFLAGS='%s' LIBS='%s' " % (dep_name , CFLAGS, LIBS))

        return env

    def _try_make_dir(self, folder):
        try:
            os.mkdir(folder)
        except OSError:
            #dir already exist
            pass


    ########################################## Helpers ###############################################

    def download_ftp(self, url, filename):
        self.output.info("downloading ftp file from url: " + url)
        
        from ftplib import FTP, FTP_TLS
        from urlparse import urlparse

        u = urlparse(url)

        host = u.netloc
        paths = u.path.split("/")
        url_filename = paths[-1]
        paths = paths[ : -1]

#        try:
#            ftp = FTP_TLS(host)
#        except:
#            ftp = FTP(host)
        ftp = FTP(host)

        ftp.login()

        if paths:
            ftp.cwd('/'.join(paths))

        file = open(filename, 'wb')
        ftp.retrbinary('RETR %s' % url_filename, file.write)


    def uncompress_xz(self, filename):
        try:
            self.uncompress_xz_3_3(filename)
            return
        except:
            self.output.info("Could not uncompress with tarfile, maybe not running on python >=3.3")
        
        try:
            self.uncompress_lzma(filename)
            return
        except:
            self.output.info("Failed to uncompress with lzma library")
            
        self.output.info("try running tar")
        
        self.uncompress_tar(filename)
        
    def uncompress_xz_3_3(self, filename):
        import tarfile

        with tarfile.open(filename) as f:
            f.extractall('.')
            
    def uncompress_lzma(self, filename):
        import contextlib
        import lzma
        import tarfile
        
        with contextlib.closing(lzma.LZMAFile(filename)) as xz:
            with tarfile.open(fileobj=xz) as f:
                f.extractall('.')
                
    def uncompress_tar(self, filename):
        cmd = "tar xvfJ " + filename
        self.output.info(cmd)
        self.run(cmd) 

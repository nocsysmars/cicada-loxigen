# Copyright 2013, Big Switch Networks, Inc.
#
# LoxiGen is licensed under the Eclipse Public License, version 1.0 (EPL), with
# the following special exception:
#
# LOXI Exception
#
# As a special exception to the terms of the EPL, you may distribute libraries
# generated by LoxiGen (LoxiGen Libraries) under the terms of your choice, provided
# that copyright and licensing notices generated by LoxiGen are not altered or removed
# from the LoxiGen Libraries and the notice provided below is (i) included in
# the LoxiGen Libraries, if distributed in source code form and (ii) included in any
# documentation for the LoxiGen Libraries, if distributed in binary form.
#
# Notice: "Copyright 2013, Big Switch Networks, Inc. This library was generated by the LoxiGen Compiler."
#
# You may not use this file except in compliance with the EPL or LOXI Exception. You may obtain
# a copy of the EPL at:
#
# http://www.eclipse.org/legal/epl-v10.html
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# EPL for the specific language governing permissions and limitations
# under the EPL.

"""
@brief Validator function generation

Generates validator function files.

"""

import sys
import c_gen.of_g_legacy as of_g
import c_gen.match as match
import c_gen.flags as flags
from generic_utils import *
import c_gen.type_maps as type_maps
import loxi_utils.loxi_utils as loxi_utils
import c_gen.loxi_utils_legacy as loxi_utils
import c_gen.identifiers as identifiers
from c_test_gen import var_name_map
from c_code_gen import v3_match_offset_get

def gen_h(out, name):
    loxi_utils.gen_c_copy_license(out)
    out.write("""
/**
 *
 * AUTOMATICALLY GENERATED FILE.  Edits will be lost on regen.
 *
 * Declarations of message validation functions. These functions check that an
 * OpenFlow message is well formed. Specifically, they check internal length
 * fields.
 */

#if !defined(_LOCI_VALIDATOR_H_)
#define _LOCI_VALIDATOR_H_

#include <loci/loci.h>

/*
 * Validate an OpenFlow message.
 * @return 0 if message is valid, -1 otherwise.
 */
extern int of_validate_message(of_message_t msg, int len);

#endif /* _LOCI_VALIDATOR_H_ */
""")

def gen_c(out, name):
    loxi_utils.gen_c_copy_license(out)
    out.write("""
/**
 *
 * AUTOMATICALLY GENERATED FILE.  Edits will be lost on regen.
 *
 * Source file for OpenFlow message validation.
 *
 */

#include "loci_log.h"
#include <loci/loci.h>
#include <loci/loci_validator.h>

#define VALIDATOR_LOG(...) LOCI_LOG_ERROR("Validator Error: " __VA_ARGS__)

""")

    # Declarations
    for version in of_g.of_version_range:
        ver_name = loxi_utils.version_to_name(version)
        for cls in reversed(of_g.standard_class_order):
            if not loxi_utils.class_in_version(cls, version):
                continue
            if cls in type_maps.inheritance_map:
                continue
            out.write("""
static inline int %(cls)s_%(ver_name)s_validate(uint8_t *buf, int len);\
""" % dict(cls=cls, ver_name=ver_name))

    out.write("\n")

    # Definitions
    for version in of_g.of_version_range:
        ver_name = loxi_utils.version_to_name(version)
        for cls in reversed(of_g.standard_class_order):
            if not loxi_utils.class_in_version(cls, version):
                continue
            if cls in type_maps.inheritance_map:
                continue
            if loxi_utils.class_is_list(cls):
                gen_list_validator(out, cls, version)
            else:
                gen_validator(out, cls, version)

        out.write("""
int
of_validate_message_%(ver_name)s(of_message_t msg, int len)
{
    of_object_id_t object_id = of_message_to_object_id(msg, len);
    uint8_t *buf = OF_MESSAGE_TO_BUFFER(msg);
    switch (object_id) {
""" % dict(ver_name=ver_name))
        for cls in reversed(of_g.standard_class_order):
            if not loxi_utils.class_in_version(cls, version):
                continue
            if cls in type_maps.inheritance_map:
                continue
            if loxi_utils.class_is_message(cls):
                out.write("""\
    case %(cls_id)s:
        return %(cls)s_%(ver_name)s_validate(buf, len);
""" % dict(ver_name=ver_name, cls=cls, cls_id=cls.upper()))
        out.write("""\
    default:
        VALIDATOR_LOG("%(cls)s: could not map %(cls_id)s");
        return -1;
    }
}
""" % dict(ver_name=ver_name, cls=cls, cls_id=cls.upper()))

    out.write("""
int
of_validate_message(of_message_t msg, int len)
{
    of_version_t version;
    if (len < OF_MESSAGE_MIN_LENGTH ||
        len != of_message_length_get(msg)) {
        VALIDATOR_LOG("message length %d != %d", len,
                      of_message_length_get(msg));
        return -1;
    }

    version = of_message_version_get(msg);
    switch (version) {
""")

    for version in of_g.of_version_range:
        ver_name = loxi_utils.version_to_name(version)
        out.write("""\
    case %(ver_name)s:
        return of_validate_message_%(ver_name)s(msg, len);
""" % dict(ver_name=ver_name))

    out.write("""\
    default:
        VALIDATOR_LOG("Bad version %%d", %(ver_name)s);
        return -1;
    }
}
""" % dict(ver_name=ver_name))

def gen_validator(out, cls, version):
    fixed_len = of_g.base_length[(cls, version)];
    ver_name = loxi_utils.version_to_name(version)
    out.write("""
static inline int
%(cls)s_%(ver_name)s_validate(uint8_t *buf, int len)
{
    if (len < %(fixed_len)s) {
        VALIDATOR_LOG("Class %(cls)s.  Len %%d too small, < %%d", len, %(fixed_len)s);
        return -1;
    }
""" % dict(cls=cls, ver_name=ver_name, cls_id=cls.upper(), fixed_len=fixed_len))
    members, member_types = loxi_utils.all_member_types_get(cls, version)
    for member in members:
        m_type = member["m_type"]
        m_name = member["name"]
        m_offset = member['offset']
        m_cls = m_type[:-2] # Trim _t
        if loxi_utils.skip_member_name(m_name):
            continue
        if not loxi_utils.type_is_of_object(m_type):
            continue
        if not loxi_utils.class_is_var_len(m_cls, version):
            continue
        if cls == "of_packet_out" and m_name == "actions":
            # See _PACKET_OUT_ACTION_LEN
            out.write("""
    {
        uint16_t %(m_name)s_len;
        buf_u16_get(buf + %(m_offset)s - 2, &%(m_name)s_len);
        if (%(m_name)s_len + %(m_offset)s > len) {
            VALIDATOR_LOG("Class %(cls)s, member %(m_name)s.  "
                          "Len %%d and offset %%d too big for %%d",
                          %(m_name)s_len, %(m_offset)s, len);
            return -1;
        }
""" % dict(m_name=m_name, m_offset=m_offset, cls=cls))
        elif version >= of_g.VERSION_1_2 and loxi_utils.cls_is_flow_mod(cls) and m_name == "instructions":
            # See _FLOW_MOD_INSTRUCTIONS_OFFSET
            match_offset = v3_match_offset_get(cls)
            m_offset = '%s_offset' % m_name
            out.write("""
    {
        uint16_t %(m_name)s_len, %(m_name)s_offset;
        uint16_t match_len;
        buf_u16_get(buf + %(match_offset)s + 2, &match_len);
        %(m_name)s_offset = %(match_offset)s + OF_MATCH_BYTES(match_len);
        %(m_name)s_len = len - %(m_name)s_offset;
""" % dict(m_name=m_name, cls=cls, match_offset=match_offset))
        elif cls == "of_bsn_gentable_entry_add" and m_name == "value":
            continue;
        elif cls == "of_bsn_gentable_entry_desc_stats_entry" and m_name == "value":
            continue;
        elif cls == "of_bsn_gentable_entry_stats_entry" and m_name == "stats":
            continue;
        else:
            out.write("""

    {    int %(m_name)s_len = len - %(m_offset)s;

"""  % dict(m_name=m_name, m_offset=m_offset))
        out.write("""
        if (%(m_cls)s_%(ver_name)s_validate(buf + %(m_offset)s, %(m_name)s_len) < 0) {
            return -1;
        }
    }
""" % dict(m_name=m_name, m_cls=m_cls, ver_name=ver_name, m_offset=m_offset))
    out.write("""
    return 0;
}
""")

def gen_list_validator(out, cls, version):
    ver_name = loxi_utils.version_to_name(version)
    e_cls = loxi_utils.list_to_entry_type(cls)
    fixed_len = of_g.base_length[(e_cls, version)];
    out.write("""
static inline int
%(cls)s_%(ver_name)s_validate(uint8_t *buf, int len)
{
""" % dict(cls=cls, ver_name=ver_name, cls_id=cls.upper(), e_cls=e_cls))

    # TLV16
    if loxi_utils.class_is_tlv16(e_cls):
        subclasses = type_maps.inheritance_map[e_cls]
        out.write("""\
    while (len >= %(fixed_len)s) {
        of_object_id_t e_id;
        uint16_t e_type, e_len;
        buf_u16_get(buf, &e_type);
        buf_u16_get(buf+2, &e_len);
        e_id = %(e_cls)s_to_object_id(e_type, %(ver_name)s);
        switch (e_id) {
""" % dict(fixed_len=fixed_len, ver_name=ver_name, e_cls=e_cls))
        for subcls in subclasses:
            subcls = e_cls + '_' + subcls
            if not loxi_utils.class_in_version(subcls, version):
                continue
            out.write("""\
        case %(subcls_enum)s:
            if (%(subcls)s_%(ver_name)s_validate(buf, e_len) < 0) {
                return -1;
            }
            break;
""" % dict(ver_name=ver_name, subcls=subcls, subcls_enum=loxi_utils.enum_name(subcls)))
        out.write("""\
        default:
            return -1;
        }
        buf += e_len;
        len -= e_len;
    }
    if (len != 0) {
        return -1;
    }
""" % dict(e_cls=e_cls, ver_name=ver_name))

    # U16 len
    elif loxi_utils.class_is_u16_len(e_cls) or loxi_utils.class_is_action(e_cls):
        out.write("""\
    /* TODO verify U16 len elements */
""" % dict())

    # OXM
    elif loxi_utils.class_is_oxm(e_cls):
        out.write("""\
    /* TODO verify OXM elements */
""" % dict())

    # Fixed length
    elif not loxi_utils.class_is_var_len(e_cls, version):
        out.write("""\
    if ((len / %(fixed_len)s) * %(fixed_len)s != len) {
        return -1;
    }
""" % dict(fixed_len=fixed_len))

    # ???
    else:
        out.write("""\
    /* XXX unknown element format */
""" % dict())

    out.write("""
    return 0;
}
""")
